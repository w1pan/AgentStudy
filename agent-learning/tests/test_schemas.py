import unittest

from pydantic import ValidationError

from app.models.schemas import AdviceResponse, KcalRange, ProfileUpsert


class SchemaTests(unittest.TestCase):
    def test_range_order(self):
        with self.assertRaises(ValidationError):
            KcalRange(low=200, high=100)

    def test_profile_rejects_client_owned_fields(self):
        with self.assertRaises(ValidationError):
            ProfileUpsert(
                age=30,
                biological_sex="female",
                height_cm=165,
                current_weight_kg=60,
                deficit_preset="gentle",
                user_id="attacker",
            )

    def test_advice_requires_fixed_card_order(self):
        with self.assertRaises(ValidationError):
            AdviceResponse.model_validate({
                "record_date": "2026-08-17",
                "data_version": 1,
                "cards": [
                    {"type": "next_meal", "title": "a", "body": "b", "bullets": []},
                    {"type": "status", "title": "a", "body": "b", "bullets": []},
                    {"type": "risk_or_encouragement", "title": "a", "body": "b", "bullets": []},
                ],
            })


if __name__ == "__main__":
    unittest.main()
