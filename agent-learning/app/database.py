from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.catalog import FOOD_SEEDS, MET_SEEDS, MET_VERSION
from app.common.logger import logger
from app.photo_estimation import (
    CATEGORY_FALLBACK,
    aggregate_photo_estimate,
    bounded_grams,
    confidence_from_legacy_range,
    density_confidence,
    estimate_item,
    worst_confidence,
)


load_dotenv()

_pool: ConnectionPool | None = None
MIGRATION_DIR = Path(__file__).resolve().parents[1] / "db" / "migrations"


def _database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url
    legacy_url = os.getenv("CHECKPOINT_DATABASE_URL")
    if legacy_url:
        logger.warning("CHECKPOINT_DATABASE_URL 已弃用，请改为 DATABASE_URL")
        return legacy_url
    raise RuntimeError("DATABASE_URL 必须配置")


def initialize_database() -> None:
    global _pool
    if _pool is not None:
        return
    _pool = ConnectionPool(
        conninfo=_database_url(),
        min_size=1,
        max_size=10,
        open=False,
        kwargs={"row_factory": dict_row, "prepare_threshold": 0},
    )
    _pool.open(wait=True, timeout=15)
    with _pool.connection() as conn:
        _run_migrations(conn)
        _seed_catalogs(conn)
        _recalibrate_photo_meals(conn)


def close_database() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def get_pool() -> ConnectionPool:
    if _pool is None:
        raise RuntimeError("数据库尚未初始化")
    return _pool


@contextmanager
def connection() -> Iterator[Connection]:
    with get_pool().connection() as conn:
        yield conn


def _run_migrations(conn: Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS qingheng_schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    applied = {
        row["version"]
        for row in conn.execute("SELECT version FROM qingheng_schema_migrations").fetchall()
    }
    for path in sorted(MIGRATION_DIR.glob("*.sql")):
        if path.name in applied:
            continue
        logger.info("应用数据库迁移 %s", path.name)
        conn.execute(path.read_text(encoding="utf-8"), prepare=False)
        conn.execute(
            "INSERT INTO qingheng_schema_migrations (version) VALUES (%s)",
            (path.name,),
        )


def _seed_catalogs(conn: Connection) -> None:
    food_rows = [
        (
            item.id,
            item.name,
            list(item.aliases),
            item.category,
            item.kcal_value,
            item.uncertainty_pct,
            item.kcal_low,
            item.kcal_high,
            json.dumps(item.units, ensure_ascii=False),
            item.source_name,
            item.source_version,
            item.source_url,
        )
        for item in FOOD_SEEDS
    ]
    with conn.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO food_templates (
                id, name, aliases, category, kcal_value, uncertainty_pct,
                kcal_low, kcal_high, units,
                source_name, source_version, source_url
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                aliases = EXCLUDED.aliases,
                category = EXCLUDED.category,
                kcal_value = EXCLUDED.kcal_value,
                uncertainty_pct = EXCLUDED.uncertainty_pct,
                kcal_low = EXCLUDED.kcal_low,
                kcal_high = EXCLUDED.kcal_high,
                units = EXCLUDED.units,
                source_name = EXCLUDED.source_name,
                source_version = EXCLUDED.source_version,
                source_url = EXCLUDED.source_url,
                active = TRUE
            """,
            food_rows,
        )
        cursor.executemany(
            """
            INSERT INTO met_activities (
                id, name, met_low, met_medium, met_high, source_version
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                met_low = EXCLUDED.met_low,
                met_medium = EXCLUDED.met_medium,
                met_high = EXCLUDED.met_high,
                source_version = EXCLUDED.source_version,
                active = TRUE
            """,
            [
                (item.id, item.name, item.low, item.medium, item.high, MET_VERSION)
                for item in MET_SEEDS
            ],
        )


def _recalibrate_photo_meals(conn: Connection) -> None:
    rows = conn.execute(
        """
        SELECT
            item.*,
            meal.user_id,
            meal.record_date,
            meal.kcal_low AS meal_kcal_low,
            meal.kcal_high AS meal_kcal_high,
            meal.estimate_confidence AS meal_estimate_confidence,
            template.id AS matched_template_id,
            template.category AS template_category,
            template.kcal_value AS template_kcal_value,
            template.uncertainty_pct AS template_uncertainty_pct,
            template.source_name AS template_source_name,
            template.source_version AS template_source_version
        FROM meal_items AS item
        JOIN meal_records AS meal ON meal.id = item.meal_id
        LEFT JOIN LATERAL (
            SELECT candidate.*
            FROM food_templates AS candidate
            WHERE candidate.active = TRUE
              AND (
                candidate.id = item.template_id
                OR candidate.name = item.name
                OR item.name = ANY(candidate.aliases)
              )
            ORDER BY CASE
                WHEN candidate.id = item.template_id THEN 0
                WHEN candidate.name = item.name THEN 1
                ELSE 2
            END
            LIMIT 1
        ) AS template ON TRUE
        WHERE meal.entry_method = 'photo'
        ORDER BY item.meal_id, item.name
        """
    ).fetchall()
    if not rows:
        return

    meals: dict[object, list[dict[str, object]]] = {}
    meal_rows: dict[object, dict[str, object]] = {}
    changed_meals: set[object] = set()
    affected_days: set[tuple[str, object]] = set()
    for row in rows:
        legacy_portion = row["portion_basis"] is None
        needs_recalibration = legacy_portion or (
            row["template_id"] is None and row["matched_template_id"] is not None
        )
        if not needs_recalibration:
            estimate = round((row["kcal_low"] + row["kcal_high"]) / 2)
            uncertainty = (row["kcal_high"] - row["kcal_low"]) / 2
            meals.setdefault(row["meal_id"], []).append({
                "kcal_low": row["kcal_low"],
                "kcal_high": row["kcal_high"],
                "kcal_estimate": estimate,
                "uncertainty_kcal": uncertainty,
                "estimate_confidence": row["estimate_confidence"] or "low",
            })
            meal_rows[row["meal_id"]] = row
            continue

        portion_confidence = row["portion_confidence"] or row["estimate_confidence"] or confidence_from_legacy_range(
            row["grams_low"], row["grams_high"]
        )
        if row["grams_low"] is not None and row["grams_high"] is not None:
            raw_grams = round((row["grams_low"] + row["grams_high"]) / 2)
        else:
            raw_grams = round(float(row["quantity"]))
        category = row["template_category"] or row["category"]
        grams = bounded_grams(row["name"], category, raw_grams)

        if row["template_kcal_value"] is not None:
            density = int(row["template_kcal_value"])
            food_uncertainty = float(row["template_uncertainty_pct"])
            source_name = row["template_source_name"]
            source_version = row["template_source_version"]
        else:
            density, food_uncertainty = CATEGORY_FALLBACK.get(
                row["category"], CATEGORY_FALLBACK["other"]
            )
            source_name = "历史视觉识别 + 轻衡分类估值"
            source_version = row["source_version"]

        if legacy_portion:
            portion_uncertainty = None
            grams_range = None
            portion_basis = "visual"
            portion_detail = "历史照片按画面体积与同类常见份量重新校准"
        else:
            portion_basis = row["portion_basis"]
            portion_detail = row["portion_detail"]
            if row["grams_low"] is not None and row["grams_high"] is not None:
                grams_low_value = int(row["grams_low"])
                grams_high_value = int(row["grams_high"])
                denominator = grams_low_value + grams_high_value
                portion_uncertainty = (
                    (grams_high_value - grams_low_value) / denominator
                    if denominator > 0 else None
                )
                grams_range = (grams_low_value, grams_high_value)
            else:
                portion_uncertainty = None
                grams_range = None

        estimate, uncertainty, grams_low, grams_high, kcal_low, kcal_high = estimate_item(
            grams=grams,
            confidence=portion_confidence,
            kcal_per_100g=density,
            food_uncertainty=food_uncertainty,
            portion_uncertainty=portion_uncertainty,
            grams_range=grams_range,
        )
        estimate_source = "template" if row["matched_template_id"] is not None else "ai"
        kcal_density_confidence = density_confidence(food_uncertainty)
        estimate_confidence = worst_confidence(portion_confidence, kcal_density_confidence)
        item_changed = any((
            row["template_id"] != row["matched_template_id"],
            row["category"] != category,
            round(float(row["quantity"])) != grams,
            row["grams_low"] != grams_low,
            row["grams_high"] != grams_high,
            row["kcal_low"] != kcal_low,
            row["kcal_high"] != kcal_high,
            row["estimate_source"] != estimate_source,
            row["estimate_confidence"] != estimate_confidence,
            row["source_name"] != source_name,
            row["source_version"] != source_version,
            row.get("portion_basis") != portion_basis,
            row.get("portion_confidence") != portion_confidence,
            row.get("density_confidence") != kcal_density_confidence,
        ))
        if item_changed:
            conn.execute(
                """
                UPDATE meal_items SET
                    template_id = %s,
                    category = %s,
                    quantity = %s,
                    grams_low = %s,
                    grams_high = %s,
                    kcal_low = %s,
                    kcal_high = %s,
                    estimate_source = %s,
                    estimate_confidence = %s,
                    portion_basis = %s,
                    portion_detail = %s,
                    portion_confidence = %s,
                    density_confidence = %s,
                    source_name = %s,
                    source_version = %s
                WHERE id = %s
                """,
                (
                    row["matched_template_id"], category, grams, grams_low, grams_high,
                    kcal_low, kcal_high, estimate_source, estimate_confidence,
                    portion_basis, portion_detail,
                    portion_confidence, kcal_density_confidence, source_name, source_version,
                    row["id"],
                ),
            )
            changed_meals.add(row["meal_id"])
        meals.setdefault(row["meal_id"], []).append({
            "kcal_low": kcal_low,
            "kcal_high": kcal_high,
            "kcal_estimate": estimate,
            "uncertainty_kcal": uncertainty,
            "estimate_confidence": estimate_confidence,
        })
        meal_rows[row["meal_id"]] = row

    for meal_id, items in meals.items():
        kcal_low, kcal_high, confidence = aggregate_photo_estimate(items)
        row = meal_rows[meal_id]
        if (
            row["meal_kcal_low"] != kcal_low
            or row["meal_kcal_high"] != kcal_high
            or row["meal_estimate_confidence"] != confidence
        ):
            changed_meals.add(meal_id)

    for meal_id in changed_meals:
        items = meals[meal_id]
        kcal_low, kcal_high, confidence = aggregate_photo_estimate(items)
        row = meal_rows[meal_id]
        affected_days.add((row["user_id"], row["record_date"]))
        if (
            row["meal_kcal_low"] != kcal_low
            or row["meal_kcal_high"] != kcal_high
            or row["meal_estimate_confidence"] != confidence
        ):
            conn.execute(
                """
                UPDATE meal_records
                SET kcal_low = %s, kcal_high = %s, estimate_confidence = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (kcal_low, kcal_high, confidence, meal_id),
            )

    for user_id, record_date in affected_days:
        intake = conn.execute(
            """
            SELECT COALESCE(SUM(kcal_low), 0) AS low, COALESCE(SUM(kcal_high), 0) AS high
            FROM meal_records
            WHERE user_id = %s AND record_date = %s
            """,
            (user_id, record_date),
        ).fetchone()
        conn.execute(
            """
            UPDATE daily_summaries SET
                intake_low = %s,
                intake_high = %s,
                deficit_low = expenditure_low - %s,
                deficit_high = expenditure_high - %s,
                data_version = data_version + 1,
                updated_at = NOW()
            WHERE user_id = %s AND record_date = %s
            """,
            (intake["low"], intake["high"], intake["high"], intake["low"], user_id, record_date),
        )
    if changed_meals:
        logger.info("已校准或补全模板 %s 条照片餐食记录", len(changed_meals))
