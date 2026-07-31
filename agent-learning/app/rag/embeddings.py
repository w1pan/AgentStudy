"""Embedding service using DashScope's OpenAI-compatible API."""

import os
from typing import List

from openai import OpenAI

from app.common.logger import logger
from app.rag.config import EMBEDDING_MODEL, EMBEDDING_BATCH_SIZE


class EmbeddingService:
    """Service for generating text embeddings via OpenAI-compatible API."""

    def __init__(self) -> None:
        base_url = os.getenv("DASHSCOPE_BASE_URL")
        api_key = os.getenv("DASHSCOPE_API_KEY")

        if not base_url or not api_key:
            raise ValueError("DASHSCOPE_BASE_URL and DASHSCOPE_API_KEY must be set")

        self._client = OpenAI(base_url=base_url, api_key=api_key)
        self._model = EMBEDDING_MODEL

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        if not texts:
            return []

        cleaned_texts = [text.strip() for text in texts]
        results: List[List[float]] = []

        for i in range(0, len(cleaned_texts), EMBEDDING_BATCH_SIZE):
            batch = cleaned_texts[i : i + EMBEDDING_BATCH_SIZE]
            logger.debug(f"Embedding batch {i // EMBEDDING_BATCH_SIZE + 1}: {len(batch)} texts")

            response = self._client.embeddings.create(model=self._model, input=batch)
            batch_embeddings = [item.embedding for item in response.data]
            results.extend(batch_embeddings)

        return results

    def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a single query text."""
        embeddings = self.embed([text])
        return embeddings[0]


_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the singleton embedding service."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
