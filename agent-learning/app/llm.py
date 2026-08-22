from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Iterator, Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI


ChatMessage = dict[str, Any]


@lru_cache(maxsize=8)
def _chat_model(model: str) -> BaseChatModel:
    """Build a provider-compatible LangChain model without adding an agent loop."""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    base_url = os.getenv("DASHSCOPE_BASE_URL")
    if not api_key or not base_url:
        raise RuntimeError("DASHSCOPE_API_KEY 和 DASHSCOPE_BASE_URL 必须配置")
    timeout = float(os.getenv("DASHSCOPE_TIMEOUT_SECONDS", "100"))
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
        max_retries=0,
    )


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") in {"text", "output_text"}:
            text = block.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "".join(parts)


def invoke_chat(
    *,
    model: str,
    messages: Sequence[ChatMessage],
    **model_kwargs: Any,
) -> str:
    response = _chat_model(model).bind(**model_kwargs).invoke(list(messages))
    return _content_text(response.content)


def stream_chat(
    *,
    model: str,
    messages: Sequence[ChatMessage],
    **model_kwargs: Any,
) -> Iterator[str]:
    for chunk in _chat_model(model).bind(**model_kwargs).stream(list(messages)):
        text = _content_text(chunk.content)
        if text:
            yield text
