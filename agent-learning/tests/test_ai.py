import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.ai import (
    VisionComponent,
    VisionMeal,
    clear_advice_cache,
    generate_advice,
    photo_items,
)
from app.models.schemas import FoodTemplateResponse, KcalRange


def fake_completion(content: str):
    return SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **_: SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
                )
            )
        )
    )


class AiTrustTests(unittest.TestCase):
    def setUp(self):
        clear_advice_cache()

    def test_photo_template_uses_server_calories_and_ai_fallback_is_marked(self):
        vision = VisionMeal(
            meal_name="午餐",
            components=[
                VisionComponent(
                    name="白米饭", category="staple", grams_estimate=110,
                    confidence="medium",
                ),
                VisionComponent(
                    name="未知拌菜", category="vegetable", grams_estimate=100,
                    confidence="low",
                ),
            ],
        )
        template = FoodTemplateResponse(
            id="rice", name="白米饭", aliases=["米饭"], category="staple",
            kcal_estimate=120, uncertainty_pct=0.10,
            kcal_per_100g=KcalRange(low=108, high=132), units={"碗": 150},
            source_name="USDA FDC", source_version="2026-01", source_url=None,
        )
        with (
            patch("app.ai.analyze_meal_image", return_value=vision),
            patch("app.ai.matching_food_templates", return_value=[template]),
        ):
            items = photo_items(b"normalized-image")

        self.assertEqual((items[0]["kcal_low"], items[0]["kcal_high"]), (96, 168))
        self.assertEqual(items[0]["estimate_source"], "template")
        self.assertEqual(items[0]["kcal_estimate"], 132)
        self.assertEqual(items[1]["estimate_source"], "ai")
        self.assertEqual((items[1]["kcal_low"], items[1]["kcal_high"]), (18, 52))

    def test_duplicate_condiment_is_merged_and_portion_is_bounded(self):
        vision = VisionMeal(
            meal_name="午餐",
            components=[
                VisionComponent(name="大蒜", category="vegetable", grams_estimate=20, confidence="high"),
                VisionComponent(name="大蒜", category="vegetable", grams_estimate=25, confidence="medium"),
            ],
        )
        with (
            patch("app.ai.analyze_meal_image", return_value=vision),
            patch("app.ai.matching_food_templates", return_value=[]),
        ):
            items = photo_items(b"normalized-image")

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["quantity"], 30)
        self.assertEqual(items[0]["estimate_confidence"], "low")
        self.assertEqual(items[0]["portion_confidence"], "medium")
        self.assertEqual(items[0]["density_confidence"], "low")

    def test_countable_photo_uses_server_unit_weight_and_explains_basis(self):
        vision = VisionMeal(
            meal_name="午餐",
            components=[VisionComponent(
                name="水饺", category="mixed_dish", grams_estimate=200,
                confidence="medium", portion_basis="count", count=12,
                size_class="medium", occlusion="partial",
            )],
        )
        template = FoodTemplateResponse(
            id="dumpling", name="水煮饺子", aliases=["水饺", "饺子"],
            category="breakfast", kcal_estimate=210, uncertainty_pct=0.18,
            kcal_per_100g=KcalRange(low=172, high=248), units={"克": 1, "份": 120},
            source_name="轻衡逐食物校准模型", source_version="v3", source_url=None,
        )
        with (
            patch("app.ai.analyze_meal_image", return_value=vision),
            patch("app.ai.matching_food_templates", return_value=[template]),
        ):
            item = photo_items(b"normalized-image")[0]

        self.assertEqual(item["quantity"], 264)
        self.assertEqual((item["grams_low"], item["grams_high"]), (225, 303))
        self.assertEqual(item["portion_basis"], "count")
        self.assertEqual(item["portion_confidence"], "medium")
        self.assertEqual(item["density_confidence"], "medium")
        self.assertIn("12 个 × 22 克/个", item["portion_detail"])

    def test_advice_rejects_numbers_not_present_in_server_facts(self):
        payload = {
            "cards": [
                {"type": "status", "title": "今日状态", "body": "摄入 999", "bullets": []},
                {"type": "next_meal", "title": "下一餐", "body": "优先清淡均衡", "bullets": []},
                {"type": "risk_or_encouragement", "title": "提醒", "body": "继续记录", "bullets": []},
            ]
        }
        facts = {"date": "2026-08-17", "data_version": 1, "verified_ranges_kcal": {}}
        with patch("app.ai._client", return_value=fake_completion(json.dumps(payload, ensure_ascii=False))):
            with self.assertRaisesRegex(ValueError, "服务端事实之外"):
                generate_advice(facts)

    def test_advice_cache_reuses_same_version_and_invalidates_on_change(self):
        payload = {
            "cards": [
                {"type": "status", "title": "今日状态", "body": "记录完整", "bullets": []},
                {"type": "next_meal", "title": "下一餐", "body": "保持清淡均衡", "bullets": []},
                {"type": "risk_or_encouragement", "title": "反馈", "body": "继续保持", "bullets": []},
            ]
        }
        calls = 0

        def create(**_):
            nonlocal calls
            calls += 1
            return SimpleNamespace(
                choices=[SimpleNamespace(
                    message=SimpleNamespace(content=json.dumps(payload, ensure_ascii=False))
                )]
            )

        fake_client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        )
        facts = {"date": "2026-08-18", "data_version": 501, "verified_ranges_kcal": {}}
        with patch("app.ai._client", return_value=fake_client):
            first = generate_advice(facts)
            second = generate_advice(facts)
            changed = generate_advice({**facts, "data_version": 502})

        self.assertEqual(calls, 2)
        self.assertEqual(first, second)
        self.assertEqual(changed.data_version, 502)


if __name__ == "__main__":
    unittest.main()
