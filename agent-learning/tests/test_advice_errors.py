import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from openai import PermissionDeniedError

from app.main import app


class AdviceErrorTests(unittest.TestCase):
    def test_free_tier_error_is_actionable_for_both_provider_body_shapes(self):
        for nested in (False, True):
            with self.subTest(nested=nested):
                error = {"code": "AllocationQuota.FreeTierOnly", "message": "private-provider-message"}
                exc = PermissionDeniedError(
                    "private-provider-message",
                    response=httpx.Response(403, request=httpx.Request("POST", "https://example.test")),
                    body={"error": error} if nested else error,
                )
                with (
                    patch("app.api.v1.qingheng.advice_facts", return_value={}),
                    patch("app.api.v1.qingheng.generate_advice", side_effect=exc),
                ):
                    response = TestClient(app).post("/api/v1/advice")
                self.assertEqual(response.status_code, 503)
                self.assertIn("免费额度已用完", response.json()["detail"])
                self.assertNotIn("private-provider-message", response.text)

    def test_unexpected_error_keeps_internal_details_private(self):
        with (
            patch("app.api.v1.qingheng.advice_facts", return_value={}),
            patch("app.api.v1.qingheng.generate_advice", side_effect=ValueError("private-data")),
        ):
            response = TestClient(app).post("/api/v1/advice")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "今日建议暂时不可用，请稍后重试")
