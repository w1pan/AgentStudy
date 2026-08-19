from __future__ import annotations

from datetime import date, time
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


MealType = Literal["breakfast", "lunch", "dinner", "custom"]
EntryMethod = Literal["manual", "photo"]
EstimateSource = Literal["template", "user", "ai", "met", "manual_adjusted"]
RiskFlag = Literal["underweight_bmi", "target_below_rmr"]
BiologicalSex = Literal["male", "female"]
DeficitPreset = Literal["gentle", "standard"]
Intensity = Literal["low", "medium", "high"]
EstimateConfidence = Literal["high", "medium", "low"]
PortionBasis = Literal["count", "container", "package", "geometry", "mixed", "visual"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KcalRange(StrictModel):
    low: int = Field(ge=-20_000, le=20_000)
    high: int = Field(ge=-20_000, le=20_000)

    @model_validator(mode="after")
    def validate_order(self) -> "KcalRange":
        if self.high < self.low:
            raise ValueError("热量上限不能小于下限")
        return self


class ProfileUpsert(StrictModel):
    age: int = Field(ge=18, le=64)
    biological_sex: BiologicalSex
    height_cm: float = Field(ge=120, le=230)
    current_weight_kg: float = Field(ge=30, le=300)
    deficit_preset: DeficitPreset


class ProfileResponse(ProfileUpsert):
    bmi: float
    rmr_kcal: int
    target_deficit: KcalRange
    updated_at: str


class FoodTemplateResponse(StrictModel):
    id: str
    name: str
    aliases: list[str]
    category: str
    kcal_estimate: int
    uncertainty_pct: float
    kcal_per_100g: KcalRange
    units: dict[str, float]
    source_name: str
    source_version: str
    source_url: str | None = None


class MetActivityResponse(StrictModel):
    id: str
    name: str
    mets: dict[Intensity, float]
    source_version: str


class ManualMealItemInput(StrictModel):
    template_id: str | None = Field(default=None, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=80)
    quantity: float = Field(gt=0, le=5000)
    unit: str = Field(min_length=1, max_length=20)
    kcal: KcalRange | None = None

    @model_validator(mode="after")
    def validate_kind(self) -> "ManualMealItemInput":
        is_template = self.template_id is not None
        has_custom_field = self.name is not None or self.kcal is not None
        if is_template == has_custom_field:
            raise ValueError("每项必须且只能选择内置模板或自定义食物")
        if not is_template and (self.name is None or self.kcal is None):
            raise ValueError("自定义食物必须填写名称和热量区间")
        return self


class ManualMealWrite(StrictModel):
    meal_type: MealType
    custom_meal_name: str | None = Field(default=None, min_length=1, max_length=40)
    recorded_time: time
    items: list[ManualMealItemInput] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_custom_name(self) -> "ManualMealWrite":
        if self.meal_type == "custom" and not self.custom_meal_name:
            raise ValueError("自定义餐次必须填写名称")
        if self.meal_type != "custom" and self.custom_meal_name is not None:
            raise ValueError("固定餐次不能提交自定义名称")
        return self


class MealItemResponse(StrictModel):
    id: str
    template_id: str | None = None
    name: str
    category: str
    quantity: float
    unit: str
    grams: KcalRange | None = None
    kcal: KcalRange
    estimate_source: EstimateSource
    estimate_confidence: EstimateConfidence | None = None
    portion_basis: PortionBasis | None = None
    portion_detail: str | None = None
    portion_confidence: EstimateConfidence | None = None
    density_confidence: EstimateConfidence | None = None
    source_name: str
    source_version: str


class MealResponse(StrictModel):
    id: str
    meal_type: MealType
    custom_meal_name: str | None = None
    display_name: str
    entry_method: EntryMethod
    recorded_date: date
    recorded_time: time
    kcal: KcalRange
    estimate_confidence: EstimateConfidence | None = None
    editable: bool
    deletable: bool
    items: list[MealItemResponse]


class ExerciseWrite(StrictModel):
    activity_id: str = Field(min_length=1, max_length=80)
    intensity: Intensity
    duration_minutes: int = Field(ge=1, le=600)
    recorded_time: time
    manual_kcal: KcalRange | None = None


class ExerciseResponse(StrictModel):
    id: str
    activity_id: str
    activity_name: str
    intensity: Intensity
    duration_minutes: int
    recorded_date: date
    recorded_time: time
    kcal: KcalRange
    estimate_source: EstimateSource
    editable: bool
    deletable: bool


class WeightResponse(StrictModel):
    recorded_date: date
    weight_kg: float
    editable: bool


class WeightUpsert(StrictModel):
    weight_kg: float = Field(ge=30, le=300)


class DailySummary(StrictModel):
    record_date: date
    data_version: int
    rmr_kcal: int
    intake: KcalRange
    baseline_expenditure: KcalRange
    exercise_expenditure: KcalRange
    total_expenditure: KcalRange
    deficit: KcalRange
    target_deficit: KcalRange
    risk_flags: list[RiskFlag]


class DayDetail(StrictModel):
    summary: DailySummary
    meals: list[MealResponse]
    exercises: list[ExerciseResponse]
    weight: WeightResponse | None = None


class HistoryMonthResponse(StrictModel):
    month: str
    dates: list[date]


class ClearHistoryRequest(StrictModel):
    confirmation: Literal["清空全部历史记录"]


class AdviceCard(StrictModel):
    type: Literal["status", "next_meal", "risk_or_encouragement"]
    title: str = Field(min_length=1, max_length=60)
    body: str = Field(min_length=1, max_length=600)
    bullets: list[Annotated[str, Field(min_length=1, max_length=160)]] = Field(
        default_factory=list,
        max_length=4,
    )


class AdviceResponse(StrictModel):
    record_date: date
    data_version: int
    cards: list[AdviceCard] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def validate_card_types(self) -> "AdviceResponse":
        expected = ["status", "next_meal", "risk_or_encouragement"]
        if [card.type for card in self.cards] != expected:
            raise ValueError("建议卡必须按固定的三种类型返回")
        return self


class FollowUpMessage(StrictModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1200)


class FollowUpRequest(StrictModel):
    card_type: Literal["status", "next_meal", "risk_or_encouragement"]
    message: str = Field(min_length=1, max_length=1200)
    history: list[FollowUpMessage] = Field(default_factory=list, max_length=12)
