import os
import unittest
from datetime import date
from uuid import uuid4
from unittest.mock import patch

import psycopg
from psycopg.errors import UniqueViolation

from app.database import (
    _recalibrate_photo_meals,
    close_database,
    connection,
    initialize_database,
)
from app.models.schemas import ProfileUpsert
from app.repository import create_photo_meal, upsert_profile


TEST_DATABASE_URL = os.getenv("QINGHENG_TEST_DATABASE_URL")


@unittest.skipUnless(TEST_DATABASE_URL, "需要显式设置 QINGHENG_TEST_DATABASE_URL")
class PostgresIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.conn = psycopg.connect(TEST_DATABASE_URL)
        self.user_id = f"integration-{uuid4()}"
        self.conn.execute(
            """
            INSERT INTO profiles (
                user_id, age, biological_sex, height_cm, current_weight_kg, deficit_preset
            ) VALUES (%s, 30, 'female', 165, 60, 'gentle')
            """,
            (self.user_id,),
        )

    def tearDown(self):
        self.conn.rollback()
        self.conn.close()

    def test_daily_weight_is_unique_and_transaction_isolated(self):
        self.conn.execute(
            "INSERT INTO weight_records (user_id, record_date, weight_kg) VALUES (%s, %s, 60)",
            (self.user_id, date.today()),
        )
        with self.assertRaises(UniqueViolation):
            self.conn.execute(
                "INSERT INTO weight_records (user_id, record_date, weight_kg) VALUES (%s, %s, 61)",
                (self.user_id, date.today()),
            )

    def test_catalogs_are_seeded(self):
        foods = self.conn.execute("SELECT COUNT(*) FROM food_templates WHERE active").fetchone()[0]
        mets = self.conn.execute("SELECT COUNT(*) FROM met_activities WHERE active").fetchone()[0]
        rice = self.conn.execute(
            "SELECT kcal_value, uncertainty_pct FROM food_templates WHERE name = '白米饭'"
        ).fetchone()
        self.assertGreaterEqual(foods, 200)
        self.assertGreaterEqual(mets, 40)
        self.assertEqual(rice[0], 116)
        self.assertAlmostEqual(float(rice[1]), 0.10)

    def test_photo_repository_persists_aggregated_range_and_confidence(self):
        repository_user = f"repository-{uuid4()}"
        try:
            with patch("app.repository.LOCAL_USER_ID", repository_user):
                initialize_database()
                upsert_profile(ProfileUpsert(
                    age=30,
                    biological_sex="female",
                    height_cm=165,
                    current_weight_kg=60,
                    deficit_preset="gentle",
                ))
                meal = create_photo_meal(
                    meal_type="lunch",
                    custom_meal_name=None,
                    items=[{
                        "template_id": "staple-001",
                        "name": "白米饭",
                        "category": "staple",
                        "quantity": 250,
                        "unit": "克",
                        "grams_low": 188,
                        "grams_high": 312,
                        "kcal_low": 240,
                        "kcal_high": 360,
                        "kcal_estimate": 300,
                        "uncertainty_kcal": 60,
                        "estimate_source": "template",
                        "estimate_confidence": "medium",
                        "source_name": "集成测试模板",
                        "source_version": "test",
                    }],
                )
                self.assertEqual((meal.kcal.low, meal.kcal.high), (235, 365))
                self.assertEqual(meal.estimate_confidence, "medium")
                self.assertEqual(meal.items[0].estimate_confidence, "medium")
        finally:
            close_database()
            with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as cleanup:
                cleanup.execute("DELETE FROM profiles WHERE user_id = %s", (repository_user,))

    def test_legacy_photo_ranges_are_recalibrated_without_original_image(self):
        repository_user = f"legacy-{uuid4()}"
        meal_id = uuid4()
        item_id = uuid4()
        try:
            with patch("app.repository.LOCAL_USER_ID", repository_user):
                initialize_database()
                upsert_profile(ProfileUpsert(
                    age=30,
                    biological_sex="female",
                    height_cm=165,
                    current_weight_kg=60,
                    deficit_preset="gentle",
                ))
                with connection() as conn:
                    conn.execute(
                        """
                        INSERT INTO meal_records (
                            id, user_id, record_date, recorded_time, meal_type,
                            entry_method, kcal_low, kcal_high
                        ) VALUES (%s, %s, CURRENT_DATE, '12:00', 'lunch', 'photo', 100, 1000)
                        """,
                        (meal_id, repository_user),
                    )
                    conn.execute(
                        """
                        INSERT INTO meal_items (
                            id, meal_id, template_id, name, category, quantity, unit,
                            grams_low, grams_high, kcal_low, kcal_high, estimate_source,
                            source_name, source_version
                        ) VALUES (
                            %s, %s, 'staple-001', '白米饭', 'staple', 150, '克',
                            120, 180, 1, 999, 'template', '旧模板', 'legacy'
                        )
                        """,
                        (item_id, meal_id),
                    )
                    _recalibrate_photo_meals(conn)
                    meal = conn.execute(
                        "SELECT kcal_low, kcal_high, estimate_confidence FROM meal_records WHERE id = %s",
                        (meal_id,),
                    ).fetchone()
                    summary = conn.execute(
                        "SELECT intake_low, intake_high FROM daily_summaries WHERE user_id = %s AND record_date = CURRENT_DATE",
                        (repository_user,),
                    ).fetchone()
                self.assertEqual(meal["estimate_confidence"], "medium")
                self.assertLess(meal["kcal_high"] - meal["kcal_low"], 150)
                self.assertEqual(
                    (summary["intake_low"], summary["intake_high"]),
                    (meal["kcal_low"], meal["kcal_high"]),
                )
        finally:
            close_database()
            with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as cleanup:
                cleanup.execute("DELETE FROM profiles WHERE user_id = %s", (repository_user,))


if __name__ == "__main__":
    unittest.main()
