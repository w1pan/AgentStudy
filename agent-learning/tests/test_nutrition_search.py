import json
import os
import unittest
from unittest.mock import patch

from app.nutrition_search import (
    clear_density_search_cache,
    search_low_confidence_densities,
)


class NutritionSearchTests(unittest.TestCase):
    def setUp(self):
        clear_density_search_cache()

    def tearDown(self):
        clear_density_search_cache()

    def test_search_converts_kj_and_uses_server_side_median(self):
        captured = {}
        payload = {
            "results": [{
                "food_name": "咖喱鸡预制菜",
                "candidates": [
                    {
                        "product_name": "产品A", "energy_value": 836.8,
                        "energy_unit": "kj_per_100g", "source_label": "品牌A",
                    },
                    {
                        "product_name": "产品B", "energy_value": 220,
                        "energy_unit": "kcal_per_100g", "source_label": "品牌B",
                    },
                    {
                        "product_name": "产品C", "energy_value": 190,
                        "energy_unit": "kcal_per_100g", "source_label": "品牌C",
                    },
                    {
                        "product_name": "无标签产品", "energy_value": None,
                        "energy_unit": None, "source_label": "品牌D",
                    },
                ],
            }],
        }

        def invoke(**kwargs):
            captured.update(kwargs)
            return json.dumps(payload, ensure_ascii=False)

        with (
            patch.dict(os.environ, {
                "NUTRITION_WEB_SEARCH_ENABLED": "true",
                "NUTRITION_SEARCH_MODEL": "qwen-test",
            }, clear=False),
            patch("app.nutrition_search.invoke_chat", side_effect=invoke),
        ):
            result = search_low_confidence_densities([
                ("咖喱鸡预制菜", "mixed_dish"),
            ])

        estimate = result["咖喱鸡预制菜"]
        self.assertEqual(estimate.kcal_per_100g, 200)
        self.assertEqual(estimate.uncertainty_pct, 0.18)
        self.assertEqual(estimate.sample_count, 3)
        self.assertTrue(captured["extra_body"]["enable_search"])
        self.assertTrue(captured["extra_body"]["search_options"]["forced_search"])
        self.assertEqual(captured["extra_body"]["search_options"]["search_strategy"], "max")

    def test_search_rejects_a_single_candidate(self):
        payload = {
            "results": [{
                "food_name": "未知菜",
                "candidates": [{
                    "product_name": "产品A", "energy_value": 180,
                    "energy_unit": "kcal_per_100g", "source_label": "品牌A",
                }],
            }],
        }
        with (
            patch.dict(os.environ, {
                "NUTRITION_WEB_SEARCH_ENABLED": "true",
                "NUTRITION_SEARCH_MODEL": "qwen-test",
            }, clear=False),
            patch(
                "app.nutrition_search.invoke_chat",
                return_value=json.dumps(payload, ensure_ascii=False),
            ),
        ):
            result = search_low_confidence_densities([("未知菜", "mixed_dish")])

        self.assertEqual(result, {})

    def test_search_rejects_disagreement_that_stays_low_confidence(self):
        payload = {
            "results": [{
                "food_name": "红烧肉预制菜",
                "candidates": [
                    {
                        "product_name": "产品A", "energy_value": 90,
                        "energy_unit": "kcal_per_100g", "source_label": "品牌A",
                    },
                    {
                        "product_name": "产品B", "energy_value": 160,
                        "energy_unit": "kcal_per_100g", "source_label": "品牌B",
                    },
                ],
            }],
        }
        with (
            patch.dict(os.environ, {
                "NUTRITION_WEB_SEARCH_ENABLED": "true",
                "NUTRITION_SEARCH_MODEL": "qwen-test",
            }, clear=False),
            patch(
                "app.nutrition_search.invoke_chat",
                return_value=json.dumps(payload, ensure_ascii=False),
            ),
        ):
            result = search_low_confidence_densities([("红烧肉预制菜", "mixed_dish")])

        self.assertEqual(result, {})

if __name__ == "__main__":
    unittest.main()
