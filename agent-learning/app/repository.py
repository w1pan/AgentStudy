from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from psycopg import Connection

from app.calculations import (
    TARGET_DEFICITS,
    Range,
    baseline_expenditure,
    bmi,
    deficit_range,
    estimated_total_expenditure,
    exercise_expenditure,
    mifflin_st_jeor,
    risk_flags,
)
from app.database import connection
from app.photo_estimation import aggregate_photo_estimate
from app.models.schemas import (
    DailySummary,
    DayDetail,
    ExerciseResponse,
    ExerciseWrite,
    FoodTemplateResponse,
    HistoryMonthResponse,
    KcalRange,
    ManualMealItemInput,
    ManualMealWrite,
    MealItemResponse,
    MealResponse,
    MetActivityResponse,
    ProfileResponse,
    ProfileUpsert,
    WeightResponse,
)


LOCAL_USER_ID = "local-user"
APP_TIMEZONE = ZoneInfo("Asia/Shanghai")
MEAL_LABELS = {
    "breakfast": "早餐",
    "lunch": "午餐",
    "dinner": "晚餐",
}


def local_now() -> datetime:
    return datetime.now(APP_TIMEZONE)


def today() -> date:
    return local_now().date()


def _number(value: Decimal | float | int) -> float:
    return float(value)


def _require_profile(conn: Connection) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM profiles WHERE user_id = %s",
        (LOCAL_USER_ID,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="请先完成用户档案")
    return row


def _profile_response(row: dict[str, Any]) -> ProfileResponse:
    weight = _number(row["current_weight_kg"])
    height = _number(row["height_cm"])
    rmr = mifflin_st_jeor(weight, height, row["age"], row["biological_sex"])
    target_low, target_high = TARGET_DEFICITS[row["deficit_preset"]]
    return ProfileResponse(
        age=row["age"],
        biological_sex=row["biological_sex"],
        height_cm=height,
        current_weight_kg=weight,
        deficit_preset=row["deficit_preset"],
        bmi=bmi(weight, height),
        rmr_kcal=rmr,
        target_deficit=KcalRange(low=target_low, high=target_high),
        updated_at=row["updated_at"].isoformat(),
    )


def get_profile() -> ProfileResponse:
    with connection() as conn:
        return _profile_response(_require_profile(conn))


def upsert_profile(payload: ProfileUpsert) -> ProfileResponse:
    current_day = today()
    with connection() as conn:
        row = conn.execute(
            """
            INSERT INTO profiles (
                user_id, age, biological_sex, height_cm, current_weight_kg,
                deficit_preset, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                age = EXCLUDED.age,
                biological_sex = EXCLUDED.biological_sex,
                height_cm = EXCLUDED.height_cm,
                current_weight_kg = EXCLUDED.current_weight_kg,
                deficit_preset = EXCLUDED.deficit_preset,
                updated_at = NOW()
            RETURNING *
            """,
            (
                LOCAL_USER_ID,
                payload.age,
                payload.biological_sex,
                payload.height_cm,
                payload.current_weight_kg,
                payload.deficit_preset,
            ),
        ).fetchone()
        conn.execute(
            """
            INSERT INTO weight_records (user_id, record_date, weight_kg, updated_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (user_id, record_date) DO UPDATE SET
                weight_kg = EXCLUDED.weight_kg,
                updated_at = NOW()
            """,
            (LOCAL_USER_ID, current_day, payload.current_weight_kg),
        )
        _recompute_summary(conn, current_day, increment_version=True)
        return _profile_response(row)


def _sum_range(conn: Connection, table: str, record_date: date) -> Range:
    if table not in {"meal_records", "exercise_records"}:
        raise ValueError("不支持的汇总表")
    row = conn.execute(
        f"""
        SELECT COALESCE(SUM(kcal_low), 0) AS low, COALESCE(SUM(kcal_high), 0) AS high
        FROM {table}
        WHERE user_id = %s AND record_date = %s
        """,
        (LOCAL_USER_ID, record_date),
    ).fetchone()
    return Range(low=int(row["low"]), high=int(row["high"]))


def _recompute_summary(conn: Connection, record_date: date, *, increment_version: bool) -> dict[str, Any]:
    profile = _require_profile(conn)
    weight_row = conn.execute(
        "SELECT weight_kg FROM weight_records WHERE user_id = %s AND record_date = %s",
        (LOCAL_USER_ID, record_date),
    ).fetchone()
    weight = _number(weight_row["weight_kg"] if weight_row else profile["current_weight_kg"])
    height = _number(profile["height_cm"])
    rmr = mifflin_st_jeor(weight, height, profile["age"], profile["biological_sex"])
    baseline = baseline_expenditure(rmr)
    intake = _sum_range(conn, "meal_records", record_date)
    exercise = _sum_range(conn, "exercise_records", record_date)
    expenditure = estimated_total_expenditure(baseline, exercise)
    deficit = deficit_range(expenditure, intake)
    target_values = TARGET_DEFICITS[profile["deficit_preset"]]
    target = Range(*target_values)
    flags = risk_flags(
        weight_kg=weight,
        height_cm=height,
        rmr_kcal=rmr,
        baseline=baseline,
        target=target,
    )
    existing = conn.execute(
        "SELECT data_version FROM daily_summaries WHERE user_id = %s AND record_date = %s",
        (LOCAL_USER_ID, record_date),
    ).fetchone()
    version = 1 if existing is None else int(existing["data_version"]) + (1 if increment_version else 0)
    snapshot = json.dumps(
        {
            "age": profile["age"],
            "biological_sex": profile["biological_sex"],
            "height_cm": height,
            "weight_kg": weight,
            "deficit_preset": profile["deficit_preset"],
        },
        ensure_ascii=False,
    )
    return conn.execute(
        """
        INSERT INTO daily_summaries (
            user_id, record_date, data_version, rmr_kcal, weight_kg, profile_snapshot,
            intake_low, intake_high, baseline_low, baseline_high,
            exercise_low, exercise_high, expenditure_low, expenditure_high,
            deficit_low, deficit_high, target_low, target_high, risk_flags, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s::jsonb,
            %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, NOW()
        )
        ON CONFLICT (user_id, record_date) DO UPDATE SET
            data_version = EXCLUDED.data_version,
            rmr_kcal = EXCLUDED.rmr_kcal,
            weight_kg = EXCLUDED.weight_kg,
            profile_snapshot = EXCLUDED.profile_snapshot,
            intake_low = EXCLUDED.intake_low,
            intake_high = EXCLUDED.intake_high,
            baseline_low = EXCLUDED.baseline_low,
            baseline_high = EXCLUDED.baseline_high,
            exercise_low = EXCLUDED.exercise_low,
            exercise_high = EXCLUDED.exercise_high,
            expenditure_low = EXCLUDED.expenditure_low,
            expenditure_high = EXCLUDED.expenditure_high,
            deficit_low = EXCLUDED.deficit_low,
            deficit_high = EXCLUDED.deficit_high,
            target_low = EXCLUDED.target_low,
            target_high = EXCLUDED.target_high,
            risk_flags = EXCLUDED.risk_flags,
            updated_at = NOW()
        RETURNING *
        """,
        (
            LOCAL_USER_ID, record_date, version, rmr, weight, snapshot,
            intake.low, intake.high, baseline.low, baseline.high,
            exercise.low, exercise.high, expenditure.low, expenditure.high,
            deficit.low, deficit.high, target.low, target.high, flags,
        ),
    ).fetchone()


def _summary_response(row: dict[str, Any]) -> DailySummary:
    return DailySummary(
        record_date=row["record_date"],
        data_version=row["data_version"],
        rmr_kcal=row["rmr_kcal"],
        intake=KcalRange(low=row["intake_low"], high=row["intake_high"]),
        baseline_expenditure=KcalRange(low=row["baseline_low"], high=row["baseline_high"]),
        exercise_expenditure=KcalRange(low=row["exercise_low"], high=row["exercise_high"]),
        total_expenditure=KcalRange(low=row["expenditure_low"], high=row["expenditure_high"]),
        deficit=KcalRange(low=row["deficit_low"], high=row["deficit_high"]),
        target_deficit=KcalRange(low=row["target_low"], high=row["target_high"]),
        risk_flags=list(row["risk_flags"] or []),
    )


def _load_meals(conn: Connection, record_date: date) -> list[MealResponse]:
    meals = conn.execute(
        """
        SELECT * FROM meal_records
        WHERE user_id = %s AND record_date = %s
        ORDER BY recorded_time, created_at
        """,
        (LOCAL_USER_ID, record_date),
    ).fetchall()
    if not meals:
        return []
    meal_ids = [row["id"] for row in meals]
    items = conn.execute(
        "SELECT * FROM meal_items WHERE meal_id = ANY(%s) ORDER BY name",
        (meal_ids,),
    ).fetchall()
    grouped: dict[UUID, list[dict[str, Any]]] = {meal_id: [] for meal_id in meal_ids}
    for item in items:
        grouped[item["meal_id"]].append(item)
    is_today = record_date == today()
    result: list[MealResponse] = []
    for meal in meals:
        response_items = [
            MealItemResponse(
                id=str(item["id"]),
                template_id=item["template_id"],
                name=item["name"],
                category=item["category"],
                quantity=_number(item["quantity"]),
                unit=item["unit"],
                grams=(
                    KcalRange(low=item["grams_low"], high=item["grams_high"])
                    if item["grams_low"] is not None and item["grams_high"] is not None
                    else None
                ),
                kcal=KcalRange(low=item["kcal_low"], high=item["kcal_high"]),
                estimate_source=item["estimate_source"],
                estimate_confidence=item["estimate_confidence"],
                portion_basis=item.get("portion_basis"),
                portion_detail=item.get("portion_detail"),
                portion_confidence=item.get("portion_confidence"),
                density_confidence=item.get("density_confidence"),
                source_name=item["source_name"],
                source_version=item["source_version"],
            )
            for item in grouped[meal["id"]]
        ]
        display_name = meal["custom_meal_name"] or MEAL_LABELS[meal["meal_type"]]
        result.append(
            MealResponse(
                id=str(meal["id"]),
                meal_type=meal["meal_type"],
                custom_meal_name=meal["custom_meal_name"],
                display_name=display_name,
                entry_method=meal["entry_method"],
                recorded_date=meal["record_date"],
                recorded_time=meal["recorded_time"],
                kcal=KcalRange(low=meal["kcal_low"], high=meal["kcal_high"]),
                estimate_confidence=meal["estimate_confidence"],
                editable=is_today and meal["entry_method"] == "manual",
                deletable=is_today,
                items=response_items,
            )
        )
    return result


def _load_exercises(conn: Connection, record_date: date) -> list[ExerciseResponse]:
    rows = conn.execute(
        """
        SELECT * FROM exercise_records
        WHERE user_id = %s AND record_date = %s
        ORDER BY recorded_time, created_at
        """,
        (LOCAL_USER_ID, record_date),
    ).fetchall()
    is_today = record_date == today()
    return [
        ExerciseResponse(
            id=str(row["id"]),
            activity_id=row["activity_id"],
            activity_name=row["activity_name"],
            intensity=row["intensity"],
            duration_minutes=row["duration_minutes"],
            recorded_date=row["record_date"],
            recorded_time=row["recorded_time"],
            kcal=KcalRange(low=row["kcal_low"], high=row["kcal_high"]),
            estimate_source=row["estimate_source"],
            editable=is_today,
            deletable=is_today,
        )
        for row in rows
    ]


def _load_weight(conn: Connection, record_date: date) -> WeightResponse | None:
    row = conn.execute(
        "SELECT * FROM weight_records WHERE user_id = %s AND record_date = %s",
        (LOCAL_USER_ID, record_date),
    ).fetchone()
    if row is None:
        return None
    return WeightResponse(
        recorded_date=row["record_date"],
        weight_kg=_number(row["weight_kg"]),
        editable=record_date == today(),
    )


def get_day_detail(record_date: date) -> DayDetail:
    if record_date > today():
        raise HTTPException(status_code=400, detail="不能查看未来日期")
    with connection() as conn:
        _require_profile(conn)
        summary_row = conn.execute(
            "SELECT * FROM daily_summaries WHERE user_id = %s AND record_date = %s",
            (LOCAL_USER_ID, record_date),
        ).fetchone()
        if summary_row is None and record_date == today():
            summary_row = _recompute_summary(conn, record_date, increment_version=False)
        if summary_row is None:
            raise HTTPException(status_code=404, detail="该日期没有记录")
        return DayDetail(
            summary=_summary_response(summary_row),
            meals=_load_meals(conn, record_date),
            exercises=_load_exercises(conn, record_date),
            weight=_load_weight(conn, record_date),
        )


def history_month(month: str) -> HistoryMonthResponse:
    try:
        first_day = datetime.strptime(month, "%Y-%m").date().replace(day=1)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="月份必须使用 YYYY-MM") from exc
    if first_day.month == 12:
        next_month = first_day.replace(year=first_day.year + 1, month=1)
    else:
        next_month = first_day.replace(month=first_day.month + 1)
    with connection() as conn:
        _require_profile(conn)
        rows = conn.execute(
            """
            SELECT record_date FROM daily_summaries
            WHERE user_id = %s AND record_date >= %s AND record_date < %s
              AND (
                EXISTS (
                    SELECT 1 FROM meal_records
                    WHERE meal_records.user_id = daily_summaries.user_id
                      AND meal_records.record_date = daily_summaries.record_date
                )
                OR EXISTS (
                    SELECT 1 FROM exercise_records
                    WHERE exercise_records.user_id = daily_summaries.user_id
                      AND exercise_records.record_date = daily_summaries.record_date
                )
                OR EXISTS (
                    SELECT 1 FROM weight_records
                    WHERE weight_records.user_id = daily_summaries.user_id
                      AND weight_records.record_date = daily_summaries.record_date
                )
              )
            ORDER BY record_date
            """,
            (LOCAL_USER_ID, first_day, next_month),
        ).fetchall()
    return HistoryMonthResponse(month=month, dates=[row["record_date"] for row in rows])


def search_food_templates(query: str, limit: int = 30) -> list[FoodTemplateResponse]:
    escaped = query.strip().replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM food_templates
            WHERE active = TRUE AND (
                name ILIKE %s ESCAPE '\\' OR array_to_string(aliases, ' ') ILIKE %s ESCAPE '\\'
            )
            ORDER BY CASE WHEN name = %s THEN 0 ELSE 1 END, name
            LIMIT %s
            """,
            (pattern, pattern, query.strip(), limit),
        ).fetchall()
    return [
        FoodTemplateResponse(
            id=row["id"],
            name=row["name"],
            aliases=list(row["aliases"] or []),
            category=row["category"],
            kcal_estimate=row["kcal_value"],
            uncertainty_pct=float(row["uncertainty_pct"]),
            kcal_per_100g=KcalRange(low=row["kcal_low"], high=row["kcal_high"]),
            units={key: float(value) for key, value in row["units"].items()},
            source_name=row["source_name"],
            source_version=row["source_version"],
            source_url=row["source_url"],
        )
        for row in rows
    ]


def list_met_activities() -> list[MetActivityResponse]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM met_activities WHERE active = TRUE ORDER BY name"
        ).fetchall()
    return [
        MetActivityResponse(
            id=row["id"],
            name=row["name"],
            mets={
                "low": _number(row["met_low"]),
                "medium": _number(row["met_medium"]),
                "high": _number(row["met_high"]),
            },
            source_version=row["source_version"],
        )
        for row in rows
    ]


def matching_food_templates() -> list[FoodTemplateResponse]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM food_templates WHERE active = TRUE ORDER BY name"
        ).fetchall()
    return [
        FoodTemplateResponse(
            id=row["id"],
            name=row["name"],
            aliases=list(row["aliases"] or []),
            category=row["category"],
            kcal_estimate=row["kcal_value"],
            uncertainty_pct=float(row["uncertainty_pct"]),
            kcal_per_100g=KcalRange(low=row["kcal_low"], high=row["kcal_high"]),
            units={key: float(value) for key, value in row["units"].items()},
            source_name=row["source_name"],
            source_version=row["source_version"],
            source_url=row["source_url"],
        )
        for row in rows
    ]


def _resolve_manual_item(conn: Connection, item: ManualMealItemInput) -> dict[str, Any]:
    if item.template_id:
        template = conn.execute(
            "SELECT * FROM food_templates WHERE id = %s AND active = TRUE",
            (item.template_id,),
        ).fetchone()
        if template is None:
            raise HTTPException(status_code=422, detail=f"食物模板不存在：{item.template_id}")
        units = template["units"]
        if item.unit not in units:
            raise HTTPException(status_code=422, detail=f"{template['name']} 不支持单位 {item.unit}")
        grams = item.quantity * float(units[item.unit])
        return {
            "template_id": template["id"],
            "name": template["name"],
            "category": template["category"],
            "quantity": item.quantity,
            "unit": item.unit,
            "grams_low": round(grams),
            "grams_high": round(grams),
            "kcal_low": max(0, round(template["kcal_low"] * grams / 100)),
            "kcal_high": max(0, round(template["kcal_high"] * grams / 100)),
            "estimate_source": "template",
            "estimate_confidence": None,
            "source_name": template["source_name"],
            "source_version": template["source_version"],
        }
    assert item.name is not None and item.kcal is not None
    if item.kcal.low < 0:
        raise HTTPException(status_code=422, detail="自定义食物热量不能为负数")
    return {
        "template_id": None,
        "name": item.name,
        "category": "other",
        "quantity": item.quantity,
        "unit": item.unit,
        "grams_low": None,
        "grams_high": None,
        "kcal_low": item.kcal.low,
        "kcal_high": item.kcal.high,
        "estimate_source": "user",
        "estimate_confidence": None,
        "source_name": "用户填写",
        "source_version": "本次记录",
    }


def _insert_meal_items(conn: Connection, meal_id: UUID, items: list[dict[str, Any]]) -> None:
    with conn.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO meal_items (
                id, meal_id, template_id, name, category, quantity, unit,
                grams_low, grams_high, kcal_low, kcal_high, estimate_source,
                estimate_confidence, portion_basis, portion_detail,
                portion_confidence, density_confidence, source_name, source_version
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """,
            [
                (
                    uuid4(), meal_id, item["template_id"], item["name"], item["category"],
                    item["quantity"], item["unit"], item["grams_low"], item["grams_high"],
                    item["kcal_low"], item["kcal_high"], item["estimate_source"],
                    item.get("estimate_confidence"), item.get("portion_basis"),
                    item.get("portion_detail"), item.get("portion_confidence"),
                    item.get("density_confidence"), item["source_name"], item["source_version"],
                )
                for item in items
            ],
        )


def create_manual_meal(payload: ManualMealWrite) -> MealResponse:
    current_day = today()
    meal_id = uuid4()
    with connection() as conn:
        _require_profile(conn)
        items = [_resolve_manual_item(conn, item) for item in payload.items]
        kcal_low = sum(item["kcal_low"] for item in items)
        kcal_high = sum(item["kcal_high"] for item in items)
        conn.execute(
            """
            INSERT INTO meal_records (
                id, user_id, record_date, recorded_time, meal_type,
                custom_meal_name, entry_method, kcal_low, kcal_high
            ) VALUES (%s, %s, %s, %s, %s, %s, 'manual', %s, %s)
            """,
            (
                meal_id, LOCAL_USER_ID, current_day, payload.recorded_time,
                payload.meal_type, payload.custom_meal_name, kcal_low, kcal_high,
            ),
        )
        _insert_meal_items(conn, meal_id, items)
        _recompute_summary(conn, current_day, increment_version=True)
        return next(item for item in _load_meals(conn, current_day) if item.id == str(meal_id))


def create_photo_meal(
    *,
    meal_type: str,
    custom_meal_name: str | None,
    items: list[dict[str, Any]],
) -> MealResponse:
    current_day = today()
    meal_id = uuid4()
    with connection() as conn:
        _require_profile(conn)
        kcal_low, kcal_high, estimate_confidence = aggregate_photo_estimate(items)
        conn.execute(
            """
            INSERT INTO meal_records (
                id, user_id, record_date, recorded_time, meal_type,
                custom_meal_name, entry_method, kcal_low, kcal_high, estimate_confidence
            ) VALUES (%s, %s, %s, %s, %s, %s, 'photo', %s, %s, %s)
            """,
            (
                meal_id, LOCAL_USER_ID, current_day, local_now().time().replace(microsecond=0),
                meal_type, custom_meal_name, kcal_low, kcal_high, estimate_confidence,
            ),
        )
        _insert_meal_items(conn, meal_id, items)
        _recompute_summary(conn, current_day, increment_version=True)
        return next(item for item in _load_meals(conn, current_day) if item.id == str(meal_id))


def update_manual_meal(meal_id: UUID, payload: ManualMealWrite) -> MealResponse:
    current_day = today()
    with connection() as conn:
        meal = conn.execute(
            "SELECT * FROM meal_records WHERE id = %s AND user_id = %s",
            (meal_id, LOCAL_USER_ID),
        ).fetchone()
        if meal is None:
            raise HTTPException(status_code=404, detail="饮食记录不存在")
        if meal["record_date"] != current_day:
            raise HTTPException(status_code=409, detail="历史饮食记录只读")
        if meal["entry_method"] != "manual":
            raise HTTPException(status_code=409, detail="照片记录不可编辑，请删除后重录")
        items = [_resolve_manual_item(conn, item) for item in payload.items]
        conn.execute("DELETE FROM meal_items WHERE meal_id = %s", (meal_id,))
        conn.execute(
            """
            UPDATE meal_records SET
                recorded_time = %s, meal_type = %s, custom_meal_name = %s,
                kcal_low = %s, kcal_high = %s, updated_at = NOW()
            WHERE id = %s
            """,
            (
                payload.recorded_time, payload.meal_type, payload.custom_meal_name,
                sum(item["kcal_low"] for item in items),
                sum(item["kcal_high"] for item in items), meal_id,
            ),
        )
        _insert_meal_items(conn, meal_id, items)
        _recompute_summary(conn, current_day, increment_version=True)
        return next(item for item in _load_meals(conn, current_day) if item.id == str(meal_id))


def delete_meal(meal_id: UUID) -> None:
    current_day = today()
    with connection() as conn:
        row = conn.execute(
            "SELECT record_date FROM meal_records WHERE id = %s AND user_id = %s",
            (meal_id, LOCAL_USER_ID),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="饮食记录不存在")
        if row["record_date"] != current_day:
            raise HTTPException(status_code=409, detail="历史饮食记录只读")
        conn.execute("DELETE FROM meal_records WHERE id = %s", (meal_id,))
        _recompute_summary(conn, current_day, increment_version=True)


def upsert_weight(weight_kg: float) -> WeightResponse:
    current_day = today()
    with connection() as conn:
        _require_profile(conn)
        conn.execute(
            "UPDATE profiles SET current_weight_kg = %s, updated_at = NOW() WHERE user_id = %s",
            (weight_kg, LOCAL_USER_ID),
        )
        row = conn.execute(
            """
            INSERT INTO weight_records (user_id, record_date, weight_kg, updated_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (user_id, record_date) DO UPDATE SET
                weight_kg = EXCLUDED.weight_kg, updated_at = NOW()
            RETURNING *
            """,
            (LOCAL_USER_ID, current_day, weight_kg),
        ).fetchone()
        _recompute_summary(conn, current_day, increment_version=True)
        return WeightResponse(recorded_date=current_day, weight_kg=_number(row["weight_kg"]), editable=True)


def _resolve_exercise(conn: Connection, payload: ExerciseWrite) -> tuple[dict[str, Any], Range, str]:
    activity = conn.execute(
        "SELECT * FROM met_activities WHERE id = %s AND active = TRUE",
        (payload.activity_id,),
    ).fetchone()
    if activity is None:
        raise HTTPException(status_code=422, detail="运动项目不存在")
    if payload.manual_kcal is not None:
        if payload.manual_kcal.low < 0:
            raise HTTPException(status_code=422, detail="运动消耗不能为负数")
        return activity, Range(payload.manual_kcal.low, payload.manual_kcal.high), "manual_adjusted"
    profile = _require_profile(conn)
    met = float(activity[f"met_{payload.intensity}"])
    calculated = exercise_expenditure(_number(profile["current_weight_kg"]), payload.duration_minutes, met)
    return activity, calculated, "met"


def create_exercise(payload: ExerciseWrite) -> ExerciseResponse:
    current_day = today()
    exercise_id = uuid4()
    with connection() as conn:
        activity, kcal, source = _resolve_exercise(conn, payload)
        conn.execute(
            """
            INSERT INTO exercise_records (
                id, user_id, activity_id, activity_name, intensity, duration_minutes,
                record_date, recorded_time, kcal_low, kcal_high, estimate_source
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                exercise_id, LOCAL_USER_ID, activity["id"], activity["name"], payload.intensity,
                payload.duration_minutes, current_day, payload.recorded_time,
                kcal.low, kcal.high, source,
            ),
        )
        _recompute_summary(conn, current_day, increment_version=True)
        return next(item for item in _load_exercises(conn, current_day) if item.id == str(exercise_id))


def update_exercise(exercise_id: UUID, payload: ExerciseWrite) -> ExerciseResponse:
    current_day = today()
    with connection() as conn:
        existing = conn.execute(
            "SELECT record_date FROM exercise_records WHERE id = %s AND user_id = %s",
            (exercise_id, LOCAL_USER_ID),
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="运动记录不存在")
        if existing["record_date"] != current_day:
            raise HTTPException(status_code=409, detail="历史运动记录只读")
        activity, kcal, source = _resolve_exercise(conn, payload)
        conn.execute(
            """
            UPDATE exercise_records SET
                activity_id = %s, activity_name = %s, intensity = %s,
                duration_minutes = %s, recorded_time = %s, kcal_low = %s,
                kcal_high = %s, estimate_source = %s, updated_at = NOW()
            WHERE id = %s
            """,
            (
                activity["id"], activity["name"], payload.intensity, payload.duration_minutes,
                payload.recorded_time, kcal.low, kcal.high, source, exercise_id,
            ),
        )
        _recompute_summary(conn, current_day, increment_version=True)
        return next(item for item in _load_exercises(conn, current_day) if item.id == str(exercise_id))


def delete_exercise(exercise_id: UUID) -> None:
    current_day = today()
    with connection() as conn:
        row = conn.execute(
            "SELECT record_date FROM exercise_records WHERE id = %s AND user_id = %s",
            (exercise_id, LOCAL_USER_ID),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="运动记录不存在")
        if row["record_date"] != current_day:
            raise HTTPException(status_code=409, detail="历史运动记录只读")
        conn.execute("DELETE FROM exercise_records WHERE id = %s", (exercise_id,))
        _recompute_summary(conn, current_day, increment_version=True)


def clear_history() -> None:
    with connection() as conn:
        _require_profile(conn)
        conn.execute("DELETE FROM meal_records WHERE user_id = %s", (LOCAL_USER_ID,))
        conn.execute("DELETE FROM exercise_records WHERE user_id = %s", (LOCAL_USER_ID,))
        conn.execute("DELETE FROM weight_records WHERE user_id = %s", (LOCAL_USER_ID,))
        conn.execute("DELETE FROM daily_summaries WHERE user_id = %s", (LOCAL_USER_ID,))


def advice_facts() -> dict[str, Any]:
    detail = get_day_detail(today())
    profile = get_profile()
    return {
        "date": detail.summary.record_date.isoformat(),
        "data_version": detail.summary.data_version,
        "profile": {
            "age": profile.age,
            "biological_sex": profile.biological_sex,
            "bmi": profile.bmi,
            "deficit_preset": profile.deficit_preset,
        },
        "verified_ranges_kcal": {
            "intake": detail.summary.intake.model_dump(),
            "baseline_expenditure": detail.summary.baseline_expenditure.model_dump(),
            "exercise_expenditure": detail.summary.exercise_expenditure.model_dump(),
            "total_expenditure": detail.summary.total_expenditure.model_dump(),
            "deficit": detail.summary.deficit.model_dump(),
            "target_deficit": detail.summary.target_deficit.model_dump(),
        },
        "risk_flags": detail.summary.risk_flags,
        "meals": [
            {
                "meal_type": meal.meal_type,
                "name": meal.display_name,
                "kcal": meal.kcal.model_dump(),
                "items": [
                    {
                        "name": item.name,
                        "category": item.category,
                        "kcal": item.kcal.model_dump(),
                        "source": item.estimate_source,
                    }
                    for item in meal.items
                ],
            }
            for meal in detail.meals
        ],
        "exercises": [
            {
                "name": item.activity_name,
                "duration_minutes": item.duration_minutes,
                "kcal": item.kcal.model_dump(),
            }
            for item in detail.exercises
        ],
    }
