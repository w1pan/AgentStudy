import unittest

from app.calculations import (
    Range,
    add_ranges,
    baseline_expenditure,
    bmi,
    deficit_range,
    exercise_expenditure,
    estimated_total_expenditure,
    mifflin_st_jeor,
    risk_flags,
)


class CalculationTests(unittest.TestCase):
    def test_mifflin_formula_for_both_sexes(self):
        self.assertEqual(mifflin_st_jeor(70, 175, 30, "male"), 1649)
        self.assertEqual(mifflin_st_jeor(70, 175, 30, "female"), 1483)

    def test_ranges_preserve_uncertainty(self):
        baseline = baseline_expenditure(1500)
        self.assertEqual(baseline, Range(1800, 1800))
        total = add_ranges(baseline, Range(180, 240))
        self.assertEqual(total, Range(1980, 2040))
        fixed_total = estimated_total_expenditure(baseline, Range(180, 240))
        self.assertEqual(fixed_total, Range(2010, 2010))
        self.assertEqual(deficit_range(fixed_total, Range(1300, 1500)), Range(510, 710))

    def test_exercise_and_bmi(self):
        self.assertEqual(exercise_expenditure(60, 30, 4), Range(113, 139))
        self.assertEqual(bmi(60, 165), 22.0)

    def test_risk_flags_are_warnings(self):
        flags = risk_flags(
            weight_kg=45,
            height_cm=170,
            rmr_kcal=1300,
            baseline=Range(1400, 1600),
            target=Range(500, 600),
        )
        self.assertIn("underweight_bmi", flags)
        self.assertIn("target_below_rmr", flags)


if __name__ == "__main__":
    unittest.main()
