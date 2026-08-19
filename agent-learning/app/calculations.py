from __future__ import annotations

from dataclasses import dataclass


TARGET_DEFICITS = {
    "gentle": (250, 350),
    "standard": (500, 600),
}


@dataclass(frozen=True)
class Range:
    low: int
    high: int


def mifflin_st_jeor(weight_kg: float, height_cm: float, age: int, biological_sex: str) -> int:
    sex_adjustment = 5 if biological_sex == "male" else -161
    return round(10 * weight_kg + 6.25 * height_cm - 5 * age + sex_adjustment)


def bmi(weight_kg: float, height_cm: float) -> float:
    return round(weight_kg / ((height_cm / 100) ** 2), 1)


def baseline_expenditure(rmr_kcal: int) -> Range:
    daily = round(rmr_kcal * 1.2)
    return Range(low=daily, high=daily)


def estimated_total_expenditure(baseline: Range, exercise: Range) -> Range:
    estimate = round((baseline.low + baseline.high + exercise.low + exercise.high) / 2)
    return Range(low=estimate, high=estimate)


def exercise_expenditure(weight_kg: float, minutes: int, met: float) -> Range:
    estimate = met * 3.5 * weight_kg / 200 * minutes
    return Range(low=max(0, round(estimate * 0.9)), high=max(0, round(estimate * 1.1)))


def add_ranges(*ranges: Range) -> Range:
    return Range(sum(item.low for item in ranges), sum(item.high for item in ranges))


def deficit_range(expenditure: Range, intake: Range) -> Range:
    return Range(low=expenditure.low - intake.high, high=expenditure.high - intake.low)


def risk_flags(
    *,
    weight_kg: float,
    height_cm: float,
    rmr_kcal: int,
    baseline: Range,
    target: Range,
) -> list[str]:
    flags: list[str] = []
    if bmi(weight_kg, height_cm) < 18.5:
        flags.append("underweight_bmi")
    if baseline.low - target.high < rmr_kcal:
        flags.append("target_below_rmr")
    return flags
