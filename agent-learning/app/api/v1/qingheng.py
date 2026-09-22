from __future__ import annotations

import asyncio
import json
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse

from app.ai import generate_advice, photo_items, stream_follow_up
from app.common.logger import logger
from app.llm import chat_failure_detail
from app.images import read_and_normalize_image
from app.models.schemas import (
    AdviceResponse,
    ClearHistoryRequest,
    DayDetail,
    ExerciseResponse,
    ExerciseWrite,
    FollowUpRequest,
    FoodTemplateResponse,
    HistoryMonthResponse,
    ManualMealWrite,
    MealResponse,
    MealType,
    MetActivityResponse,
    ProfileResponse,
    ProfileUpsert,
    WeightResponse,
    WeightUpsert,
)
from app.repository import (
    advice_facts,
    clear_history,
    create_exercise,
    create_manual_meal,
    create_photo_meal,
    delete_exercise,
    delete_meal,
    get_day_detail,
    get_profile,
    history_month,
    list_met_activities,
    search_food_templates,
    today,
    update_exercise,
    update_manual_meal,
    upsert_profile,
    upsert_weight,
)


router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/profile", response_model=ProfileResponse)
def read_profile() -> ProfileResponse:
    return get_profile()


@router.put("/profile", response_model=ProfileResponse)
def write_profile(payload: ProfileUpsert) -> ProfileResponse:
    return upsert_profile(payload)


@router.get("/today", response_model=DayDetail)
def read_today() -> DayDetail:
    return get_day_detail(today())


@router.get("/history", response_model=HistoryMonthResponse)
def read_history_month(
    month: Annotated[str, Query(pattern=r"^\d{4}-\d{2}$")],
) -> HistoryMonthResponse:
    return history_month(month)


@router.post("/history/clear", status_code=204)
def clear_history_endpoint(_: ClearHistoryRequest) -> Response:
    clear_history()
    return Response(status_code=204)


@router.get("/history/{record_date}", response_model=DayDetail)
def read_history_day(record_date: date) -> DayDetail:
    return get_day_detail(record_date)


@router.get("/food-templates", response_model=list[FoodTemplateResponse])
def food_templates(
    query: Annotated[str, Query(min_length=1, max_length=80)],
) -> list[FoodTemplateResponse]:
    return search_food_templates(query)


@router.get("/met-activities", response_model=list[MetActivityResponse])
def met_activities() -> list[MetActivityResponse]:
    return list_met_activities()


@router.post("/meals/manual", response_model=MealResponse, status_code=201)
def add_manual_meal(payload: ManualMealWrite) -> MealResponse:
    return create_manual_meal(payload)


@router.post("/meals/photo", response_model=MealResponse, status_code=201)
async def add_photo_meal(
    request: Request,
    meal_type: Annotated[MealType, Query()],
    custom_meal_name: Annotated[str | None, Query(min_length=1, max_length=40)] = None,
) -> MealResponse:
    if meal_type == "custom" and not custom_meal_name:
        raise HTTPException(status_code=422, detail="自定义餐次必须填写名称")
    if meal_type != "custom" and custom_meal_name is not None:
        raise HTTPException(status_code=422, detail="固定餐次不能提交自定义名称")
    normalized = await read_and_normalize_image(request)
    try:
        items = await asyncio.to_thread(photo_items, normalized)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="照片识别暂时不可用，请重试或手动记录") from exc
    if not items:
        raise HTTPException(status_code=422, detail="未识别到可记录的食物")
    return await asyncio.to_thread(
        create_photo_meal,
        meal_type=meal_type,
        custom_meal_name=custom_meal_name,
        items=items,
    )


@router.patch("/meals/{meal_id}", response_model=MealResponse)
def edit_manual_meal(meal_id: UUID, payload: ManualMealWrite) -> MealResponse:
    return update_manual_meal(meal_id, payload)


@router.delete("/meals/{meal_id}", status_code=204)
def remove_meal(meal_id: UUID) -> Response:
    delete_meal(meal_id)
    return Response(status_code=204)


@router.put("/weights/today", response_model=WeightResponse)
def write_today_weight(payload: WeightUpsert) -> WeightResponse:
    return upsert_weight(payload.weight_kg)


@router.post("/exercises", response_model=ExerciseResponse, status_code=201)
def add_exercise(payload: ExerciseWrite) -> ExerciseResponse:
    return create_exercise(payload)


@router.patch("/exercises/{exercise_id}", response_model=ExerciseResponse)
def edit_exercise(exercise_id: UUID, payload: ExerciseWrite) -> ExerciseResponse:
    return update_exercise(exercise_id, payload)


@router.delete("/exercises/{exercise_id}", status_code=204)
def remove_exercise(exercise_id: UUID) -> Response:
    delete_exercise(exercise_id)
    return Response(status_code=204)


@router.post("/advice", response_model=AdviceResponse)
def advice() -> AdviceResponse:
    facts = advice_facts()
    try:
        return generate_advice(facts)
    except Exception as exc:
        detail = chat_failure_detail(exc)
        # Do not log provider bodies: they may contain request data or credentials.
        logger.error("今日建议失败 kind=%s detail=%s", type(exc).__name__, detail)
        raise HTTPException(status_code=503, detail=detail) from exc


@router.post("/advice/follow-up")
def advice_follow_up(payload: FollowUpRequest) -> StreamingResponse:
    facts = advice_facts()
    history = [message.model_dump() for message in payload.history]

    def events():
        try:
            for text in stream_follow_up(
                facts=facts,
                card_type=payload.card_type,
                message=payload.message,
                history=history,
            ):
                yield "data: " + json.dumps({"text": text}, ensure_ascii=False) + "\n\n"
            yield "event: done\ndata: {}\n\n"
        except Exception:
            yield "event: error\ndata: " + json.dumps(
                {"detail": "追问暂时不可用，请稍后重试"},
                ensure_ascii=False,
            ) + "\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
