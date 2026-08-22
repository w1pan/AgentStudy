import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.llm import _chat_model, invoke_chat, stream_chat


class LangChainModelLayerTests(unittest.TestCase):
    def tearDown(self):
        _chat_model.cache_clear()

    def test_dashscope_configuration_is_centralized_in_chat_model(self):
        with (
            patch.dict(os.environ, {
                "DASHSCOPE_API_KEY": "test-key",
                "DASHSCOPE_BASE_URL": "https://example.test/v1",
                "DASHSCOPE_TIMEOUT_SECONDS": "42",
            }, clear=False),
            patch("app.llm.ChatOpenAI") as chat_openai,
        ):
            _chat_model.cache_clear()
            _chat_model("qwen-test")

        chat_openai.assert_called_once_with(
            model="qwen-test",
            api_key="test-key",
            base_url="https://example.test/v1",
            timeout=42.0,
            max_retries=0,
        )

    def test_invoke_chat_binds_provider_options_and_returns_text(self):
        bound = MagicMock()
        bound.invoke.return_value = SimpleNamespace(content="structured result")
        model = MagicMock()
        model.bind.return_value = bound

        with patch("app.llm._chat_model", return_value=model):
            result = invoke_chat(
                model="qwen-test",
                messages=[{"role": "user", "content": "hello"}],
                temperature=0,
                response_format={"type": "json_object"},
            )

        model.bind.assert_called_once_with(
            temperature=0,
            response_format={"type": "json_object"},
        )
        bound.invoke.assert_called_once()
        self.assertEqual(result, "structured result")

    def test_stream_chat_normalizes_text_blocks(self):
        bound = MagicMock()
        bound.stream.return_value = iter([
            SimpleNamespace(content="第一段"),
            SimpleNamespace(content=[{"type": "text", "text": "第二段"}]),
        ])
        model = MagicMock()
        model.bind.return_value = bound

        with patch("app.llm._chat_model", return_value=model):
            result = list(stream_chat(
                model="qwen-test",
                messages=[{"role": "user", "content": "hello"}],
                temperature=0.2,
            ))

        self.assertEqual(result, ["第一段", "第二段"])


if __name__ == "__main__":
    unittest.main()
