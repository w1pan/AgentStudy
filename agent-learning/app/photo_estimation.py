from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any


PORTION_UNCERTAINTY = {"high": 0.15, "medium": 0.25, "low": 0.40}
MEAL_LEVEL_UNCERTAINTY = 0.04
CONFIDENCE_RANK = {"high": 0, "medium": 1, "low": 2}
STRATEGY_UNCERTAINTY = {
    "count": {"high": 0.08, "medium": 0.12, "low": 0.20},
    "container": {"high": 0.14, "medium": 0.19, "low": 0.28},
    "package": {"high": 0.04, "medium": 0.07, "low": 0.12},
    "geometry": {"high": 0.14, "medium": 0.20, "low": 0.30},
    "mixed": {"high": 0.18, "medium": 0.25, "low": 0.36},
    "visual": PORTION_UNCERTAINTY,
}
CATEGORY_PORTION_MAX = {
    "staple": 700,
    "breakfast": 700,
    "protein": 500,
    "vegetable": 600,
    "fruit": 700,
    "dairy": 800,
    "snack": 350,
    "snack_drink": 1500,
    "drink": 1500,
    "mixed_dish": 1200,
    "other": 900,
}
CATEGORY_FALLBACK = {
    "staple": (135, 0.22),
    "breakfast": (170, 0.25),
    "protein": (170, 0.25),
    "vegetable": (35, 0.25),
    "fruit": (60, 0.20),
    "dairy": (65, 0.22),
    "snack": (320, 0.30),
    "snack_drink": (80, 0.35),
    "drink": (40, 0.30),
    "mixed_dish": (165, 0.28),
    "other": (150, 0.35),
}
SPECIAL_PORTION_MAX = {
    "大蒜": 30,
    "蒜": 30,
    "葱": 30,
    "姜": 30,
    "辣椒酱": 50,
    "沙拉酱": 80,
    "食用油": 50,
}

# 单个可食用重量是服务端先验，模型只负责计数和判断大小。
# 数值用于日常记录，不表示称重级精度。
COUNTABLE_PORTIONS: dict[str, tuple[int, int, int]] = {
    "水煮饺子": (18, 22, 28), "猪肉水饺": (18, 22, 28),
    "素饺子": (17, 21, 27), "虾仁饺子": (18, 23, 29),
    "云吞": (12, 18, 25), "馄饨": (12, 18, 25),
    "小笼包": (25, 35, 50), "菜包": (60, 90, 120),
    "肉包": (70, 100, 140), "烧卖": (20, 30, 45),
    "水煮蛋": (45, 55, 65), "茶叶蛋": (45, 55, 65),
    "煎鸡蛋": (45, 55, 65), "荷包蛋": (45, 55, 65),
    "鸡翅": (30, 45, 60), "基围虾": (10, 15, 22),
    "全麦吐司": (20, 28, 40), "白吐司": (20, 28, 40),
    "贝果": (70, 95, 130), "能量棒": (35, 50, 70),
    "蛋白棒": (35, 50, 70), "奶酪棒": (15, 20, 30),
    "苹果": (120, 180, 250), "香蕉": (70, 100, 140),
    "橙子": (100, 150, 220), "梨": (120, 180, 260),
    "桃": (100, 150, 220), "猕猴桃": (60, 85, 120),
    "牛油果": (100, 150, 220),
}
COUNTABLE_ALIASES = {
    "饺子": "水煮饺子", "水饺": "水煮饺子", "煮饺": "水煮饺子",
    "猪肉饺子": "猪肉水饺", "鲜肉水饺": "猪肉水饺",
}
CONTAINER_CAPACITY_ML = {
    "small_bowl": 250,
    "medium_bowl": 400,
    "large_bowl": 650,
    "cup": 300,
    "glass": 350,
}
NAME_BULK_DENSITY = {
    "白米饭": 0.70, "糙米饭": 0.68, "杂粮饭": 0.68,
    "煮面条": 0.55, "米线": 0.58, "米粉": 0.58, "河粉": 0.55,
    "白粥": 1.00, "小米粥": 1.00, "杂粮粥": 1.00,
    "燕麦粥": 1.00, "豆浆": 1.02, "牛奶": 1.03,
    "酸奶": 1.04, "汤": 1.00, "饮料": 1.00,
}
CATEGORY_BULK_DENSITY = {
    "staple": 0.68, "protein": 0.65, "vegetable": 0.35,
    "fruit": 0.60, "dairy": 1.03, "snack": 0.55,
    "drink": 1.00, "mixed_dish": 0.78, "other": 0.70,
}
SIZE_LABELS = {"small": "小份", "medium": "中等", "large": "大份"}
CONTAINER_LABELS = {
    "small_bowl": "小碗", "medium_bowl": "中碗", "large_bowl": "大碗",
    "cup": "杯", "glass": "玻璃杯",
}


@dataclass(frozen=True)
class PortionEstimate:
    grams: int
    grams_low: int
    grams_high: int
    uncertainty: float
    basis: str
    detail: str
    confidence: str


def _normalize_name(value: str) -> str:
    return re.sub(r"[\s（）()、，,·的]+", "", value.lower())


def _countable_weights(name: str) -> tuple[int, int, int] | None:
    normalized = _normalize_name(name)
    canonical = COUNTABLE_ALIASES.get(normalized, normalized)
    exact = COUNTABLE_PORTIONS.get(canonical)
    if exact is not None:
        return exact
    for candidate, weights in COUNTABLE_PORTIONS.items():
        normalized_candidate = _normalize_name(candidate)
        if normalized_candidate in normalized or normalized in normalized_candidate:
            return weights
    return None


def _bulk_density(name: str, category: str) -> float:
    normalized = _normalize_name(name)
    for candidate, density in NAME_BULK_DENSITY.items():
        if _normalize_name(candidate) in normalized:
            return density
    return CATEGORY_BULK_DENSITY.get(category, CATEGORY_BULK_DENSITY["other"])


def density_confidence(food_uncertainty: float) -> str:
    if food_uncertainty <= 0.12:
        return "high"
    if food_uncertainty <= 0.24:
        return "medium"
    return "low"


def estimate_portion(
    *,
    name: str,
    category: str,
    grams_estimate: int,
    confidence: str,
    portion_basis: str = "visual",
    count: int | None = None,
    size_class: str = "medium",
    container_type: str | None = None,
    fill_ratio: float | None = None,
    package_grams: int | None = None,
    occlusion: str = "none",
) -> PortionEstimate:
    """Turn model observations into a bounded, explainable server-side portion."""
    basis = portion_basis if portion_basis in STRATEGY_UNCERTAINTY else "visual"
    center = bounded_grams(name, category, grams_estimate)
    uncertainty = STRATEGY_UNCERTAINTY[basis][confidence]
    detail = "根据画面体积与同类常见份量估算"

    if basis == "count":
        weights = _countable_weights(name)
        if weights is not None and count is not None and 1 <= count <= 100:
            size_index = {"small": 0, "medium": 1, "large": 2}.get(size_class, 1)
            unit_grams = weights[size_index]
            center = bounded_grams(name, category, count * unit_grams)
            hidden_count = 0 if occlusion == "none" else 1 if occlusion == "partial" else max(1, round(count * 0.15))
            count_uncertainty = hidden_count / count
            uncertainty = min(0.35, math.sqrt(uncertainty ** 2 + count_uncertainty ** 2))
            detail = f"约 {count} 个 × {unit_grams} 克/个（{SIZE_LABELS.get(size_class, '中等')}）"
            if hidden_count:
                detail += f"，遮挡按 ±{hidden_count} 个计"
        else:
            basis = "visual"
            uncertainty = STRATEGY_UNCERTAINTY[basis][confidence]
    elif basis == "container":
        capacity = CONTAINER_CAPACITY_ML.get(container_type or "")
        if capacity is not None and fill_ratio is not None and 0.05 <= fill_ratio <= 1.0:
            density = _bulk_density(name, category)
            center = bounded_grams(name, category, round(capacity * fill_ratio * density))
            percent = round(fill_ratio * 100)
            detail = f"按{CONTAINER_LABELS[container_type]}约 {percent}% 盛装及熟食密度估算"
        else:
            basis = "visual"
            uncertainty = STRATEGY_UNCERTAINTY[basis][confidence]
    elif basis == "package":
        if package_grams is not None and 1 <= package_grams <= 5000:
            fraction = fill_ratio if fill_ratio is not None and 0.05 <= fill_ratio <= 1.0 else 1.0
            center = bounded_grams(name, category, round(package_grams * fraction))
            detail = f"按包装净含量 {package_grams} 克"
            if fraction < 1:
                detail += f" × 可见食用比例 {round(fraction * 100)}%"
        else:
            basis = "visual"
            uncertainty = STRATEGY_UNCERTAINTY[basis][confidence]
    elif basis == "geometry":
        detail = f"按规则形状、{SIZE_LABELS.get(size_class, '中等')}厚度和食物密度估算"
    elif basis == "mixed":
        detail = "按整道菜可见体积估算；配方和用油另计热量密度误差"

    grams_low = max(1, round(center * (1 - uncertainty)))
    grams_high = max(grams_low, round(center * (1 + uncertainty)))
    return PortionEstimate(
        grams=center,
        grams_low=grams_low,
        grams_high=grams_high,
        uncertainty=uncertainty,
        basis=basis,
        detail=detail,
        confidence=confidence,
    )


def worst_confidence(left: str, right: str) -> str:
    return left if CONFIDENCE_RANK[left] >= CONFIDENCE_RANK[right] else right


def bounded_grams(name: str, category: str, grams: int) -> int:
    special_max = SPECIAL_PORTION_MAX.get(_normalize_name(name))
    maximum = special_max or CATEGORY_PORTION_MAX.get(category, CATEGORY_PORTION_MAX["other"])
    return max(1, min(grams, maximum))


def confidence_from_legacy_range(low: int | None, high: int | None) -> str:
    if low is None or high is None or low <= 0 or high < low:
        return "low"
    relative_half_width = (high - low) / (high + low)
    if relative_half_width <= 0.18:
        return "high"
    if relative_half_width <= 0.30:
        return "medium"
    return "low"


def estimate_item(
    *,
    grams: int,
    confidence: str,
    kcal_per_100g: int,
    food_uncertainty: float,
    portion_uncertainty: float | None = None,
    grams_range: tuple[int, int] | None = None,
) -> tuple[int, int, int, int, int, int]:
    estimate = max(0, round(kcal_per_100g * grams / 100))
    portion_uncertainty = (
        PORTION_UNCERTAINTY[confidence]
        if portion_uncertainty is None
        else max(0.02, min(portion_uncertainty, 0.60))
    )
    combined_uncertainty = min(
        0.60,
        math.sqrt(portion_uncertainty ** 2 + food_uncertainty ** 2),
    )
    uncertainty_kcal = max(3, round(estimate * combined_uncertainty)) if estimate else 1
    if grams_range is None:
        grams_low = max(1, round(grams * (1 - portion_uncertainty)))
        grams_high = round(grams * (1 + portion_uncertainty))
    else:
        grams_low, grams_high = grams_range
    kcal_low = max(0, estimate - uncertainty_kcal)
    kcal_high = estimate + uncertainty_kcal
    return estimate, uncertainty_kcal, grams_low, grams_high, kcal_low, kcal_high


def aggregate_photo_estimate(items: list[dict[str, Any]]) -> tuple[int, int, str]:
    if not items:
        raise ValueError("照片餐食至少需要一项组成")
    kcal_estimate = sum(
        item.get("kcal_estimate", round((item["kcal_low"] + item["kcal_high"]) / 2))
        for item in items
    )
    independent_uncertainty = math.sqrt(sum(
        item.get("uncertainty_kcal", (item["kcal_high"] - item["kcal_low"]) / 2) ** 2
        for item in items
    ))
    meal_level_uncertainty = kcal_estimate * MEAL_LEVEL_UNCERTAINTY
    total_uncertainty = round(math.sqrt(
        independent_uncertainty ** 2 + meal_level_uncertainty ** 2
    ))
    relative_uncertainty = total_uncertainty / kcal_estimate if kcal_estimate else 1.0
    if relative_uncertainty <= 0.18:
        confidence = "high"
    elif relative_uncertainty <= 0.30:
        confidence = "medium"
    else:
        confidence = "low"
    return max(0, kcal_estimate - total_uncertainty), kcal_estimate + total_uncertainty, confidence
