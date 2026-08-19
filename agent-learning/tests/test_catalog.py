import unittest

from app.catalog import FOOD_SEEDS, MET_SEEDS


class CatalogTests(unittest.TestCase):
    def test_food_catalog_is_large_and_versioned(self):
        self.assertGreaterEqual(len(FOOD_SEEDS), 200)
        self.assertEqual(len({item.id for item in FOOD_SEEDS}), len(FOOD_SEEDS))
        self.assertTrue(all(item.source_version for item in FOOD_SEEDS))
        self.assertTrue(all("克" in item.units for item in FOOD_SEEDS))
        self.assertTrue(all(item.kcal_low <= item.kcal_value <= item.kcal_high for item in FOOD_SEEDS))
        by_name = {item.name: item for item in FOOD_SEEDS}
        self.assertEqual(by_name["白米饭"].kcal_value, 116)
        self.assertEqual(by_name["番茄"].kcal_value, 18)
        self.assertEqual(by_name["牛肉饼"].kcal_value, 250)
        self.assertNotEqual(by_name["鸡翅"].kcal_value, by_name["鳕鱼"].kcal_value)

    def test_met_catalog_has_expected_coverage(self):
        self.assertEqual(len(MET_SEEDS), 40)
        self.assertEqual(len({item.id for item in MET_SEEDS}), 40)
        self.assertTrue(all(item.low <= item.medium <= item.high for item in MET_SEEDS))


if __name__ == "__main__":
    unittest.main()
