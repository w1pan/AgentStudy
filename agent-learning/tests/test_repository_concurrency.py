import json
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch
from uuid import uuid4

from app import repository
from app.ai import clear_advice_cache, generate_advice
from app.database import close_database, connection, initialize_database
from app.models.schemas import ManualMealWrite, ProfileUpsert


TEST_DATABASE_URL = os.getenv("QINGHENG_TEST_DATABASE_URL")


@unittest.skipUnless(TEST_DATABASE_URL, "需要显式设置 QINGHENG_TEST_DATABASE_URL")
class RepositoryConcurrencyTests(unittest.TestCase):
    def setUp(self):
        database_env = patch.dict(os.environ, {"DATABASE_URL": TEST_DATABASE_URL})
        database_env.start()
        self.addCleanup(database_env.stop)
        close_database()
        self.addCleanup(close_database)
        initialize_database()
        self.user_id = f"concurrency-{uuid4()}"
        user_patch = patch("app.repository.LOCAL_USER_ID", self.user_id)
        user_patch.start()
        self.addCleanup(user_patch.stop)
        self.addCleanup(self._delete_user)
        repository.upsert_profile(ProfileUpsert(
            age=30, biological_sex="female", height_cm=165,
            current_weight_kg=60, deficit_preset="gentle",
        ))

    def _delete_user(self):
        with connection() as conn:
            conn.execute("DELETE FROM profiles WHERE user_id = %s", (self.user_id,))

    def _meal(self, kcal):
        return ManualMealWrite.model_validate({
            "meal_type": "lunch", "recorded_time": "12:00",
            "items": [{"name": "测试食物", "quantity": 1, "unit": "份",
                       "kcal": {"low": kcal, "high": kcal}}],
        })

    def _run_overlapping_requests(self, first_action, second_action):
        first_ready = Event()
        release_first = Event()
        second_started = Event()
        second_summed = Event()
        recompute = repository._recompute_summary
        sum_range = repository._sum_range

        def hold_first_transaction(*args, **kwargs):
            result = recompute(*args, **kwargs)
            if not first_ready.is_set():
                first_ready.set()
                if not release_first.wait(5):
                    raise TimeoutError("首个事务未释放")
            return result

        def observe_sum(conn, table, record_date):
            result = sum_range(conn, table, record_date)
            if first_ready.is_set() and table == "exercise_records":
                second_summed.set()
            return result

        def start_second():
            second_started.set()
            return second_action()

        with (
            patch("app.repository._recompute_summary", side_effect=hold_first_transaction),
            patch("app.repository._sum_range", side_effect=observe_sum),
            ThreadPoolExecutor(max_workers=2) as executor,
        ):
            first = executor.submit(first_action)
            try:
                self.assertTrue(first_ready.wait(5))
                second = executor.submit(start_second)
                self.assertTrue(second_started.wait(5))
                summed_before_commit = second_summed.wait(0.3)
            finally:
                release_first.set()
            first.result(timeout=5)
            second.result(timeout=5)
        return summed_before_commit

    def test_concurrent_meals_preserve_both_calories_and_versions(self):
        overlapped = self._run_overlapping_requests(
            lambda: repository.create_manual_meal(self._meal(100)),
            lambda: repository.create_manual_meal(self._meal(200)),
        )
        detail = repository.get_day_detail(repository.today())
        self.assertEqual(len(detail.meals), 2)
        self.assertEqual((detail.summary.intake.low, detail.summary.intake.high), (300, 300))
        self.assertEqual(detail.summary.data_version, 3)
        self.assertFalse(overlapped, "后一个事务不能汇总前一个尚未提交的写入")

    def test_lazy_summary_creation_cannot_overwrite_a_concurrent_meal(self):
        repository.clear_history()
        overlapped = self._run_overlapping_requests(
            lambda: repository.get_day_detail(repository.today()),
            lambda: repository.create_manual_meal(self._meal(120)),
        )
        detail = repository.get_day_detail(repository.today())
        self.assertEqual(len(detail.meals), 1)
        self.assertEqual((detail.summary.intake.low, detail.summary.intake.high), (120, 120))
        self.assertEqual(detail.summary.data_version, 2)
        self.assertFalse(overlapped)

    def test_advice_after_history_clear_uses_new_meals_at_a_reused_version(self):
        clear_advice_cache()
        self.addCleanup(clear_advice_cache)
        repository.create_manual_meal(self._meal(100))
        old_facts = repository.advice_facts()
        responses = [json.dumps({"cards": [
            {"type": kind, "title": "建议", "body": body, "bullets": []}
            for kind in ("status", "next_meal", "risk_or_encouragement")
        ]}, ensure_ascii=False) for body in ("旧餐食建议", "新餐食建议")]
        with patch("app.ai.invoke_chat", side_effect=responses) as invoke:
            old = generate_advice(old_facts)
            repository.clear_history()
            repository.get_day_detail(repository.today())
            repository.create_manual_meal(self._meal(200))
            new_facts = repository.advice_facts()
            self.assertEqual(new_facts["data_version"], old_facts["data_version"])
            new = generate_advice(new_facts)
        self.assertEqual(invoke.call_count, 2)
        self.assertEqual(old.cards[0].body, "旧餐食建议")
        self.assertEqual(new.cards[0].body, "新餐食建议")
