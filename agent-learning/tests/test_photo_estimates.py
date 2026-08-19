import unittest

from app.photo_estimation import aggregate_photo_estimate, estimate_item, estimate_portion


class PhotoEstimateTests(unittest.TestCase):
    def test_uncertainties_are_combined_instead_of_adding_all_extremes(self):
        items = [
            {
                "kcal_low": 80, "kcal_high": 120, "kcal_estimate": 100,
                "uncertainty_kcal": 20, "estimate_confidence": "medium",
            },
            {
                "kcal_low": 160, "kcal_high": 240, "kcal_estimate": 200,
                "uncertainty_kcal": 40, "estimate_confidence": "high",
            },
        ]
        low, high, confidence = aggregate_photo_estimate(items)
        self.assertEqual((low, high), (249, 351))
        self.assertEqual(confidence, "high")
        self.assertLess(high - low, sum(item["kcal_high"] - item["kcal_low"] for item in items))

    def test_empty_photo_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "至少需要一项"):
            aggregate_photo_estimate([])

    def test_countable_food_uses_count_and_unit_weight(self):
        portion = estimate_portion(
            name="水煮饺子", category="breakfast", grams_estimate=200,
            confidence="medium", portion_basis="count", count=12,
            size_class="medium", occlusion="partial",
        )
        self.assertEqual(portion.grams, 264)
        self.assertEqual((portion.grams_low, portion.grams_high), (225, 303))
        self.assertEqual(portion.basis, "count")
        self.assertIn("12 个 × 22 克/个", portion.detail)
        self.assertIn("±1 个", portion.detail)

    def test_container_food_uses_capacity_fill_and_bulk_density(self):
        portion = estimate_portion(
            name="白米饭", category="staple", grams_estimate=300,
            confidence="medium", portion_basis="container",
            container_type="medium_bowl", fill_ratio=0.75,
        )
        self.assertEqual(portion.grams, 210)
        self.assertEqual((portion.grams_low, portion.grams_high), (170, 250))
        self.assertIn("75%", portion.detail)

    def test_package_food_uses_visible_net_weight(self):
        portion = estimate_portion(
            name="原味酸奶", category="dairy", grams_estimate=160,
            confidence="high", portion_basis="package",
            package_grams=200, fill_ratio=0.5,
        )
        self.assertEqual((portion.grams, portion.grams_low, portion.grams_high), (100, 96, 104))
        self.assertIn("200 克", portion.detail)

    def test_invalid_count_observation_falls_back_to_visual_range(self):
        portion = estimate_portion(
            name="未知丸子", category="other", grams_estimate=200,
            confidence="medium", portion_basis="count", count=8,
        )
        self.assertEqual(portion.basis, "visual")
        self.assertEqual((portion.grams_low, portion.grams_high), (150, 250))

    def test_calorie_uncertainty_keeps_portion_and_density_independent(self):
        result = estimate_item(
            grams=200, confidence="medium", kcal_per_100g=100,
            food_uncertainty=0.10, portion_uncertainty=0.10,
            grams_range=(180, 220),
        )
        self.assertEqual(result[2:4], (180, 220))
        self.assertEqual(result[4:6], (172, 228))


if __name__ == "__main__":
    unittest.main()
