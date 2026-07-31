"""Recipe retriever for the RAG knowledge base."""

from dataclasses import dataclass
from typing import List, Optional

from qdrant_client import QdrantClient

from app.common.logger import logger
from app.rag.client import get_qdrant_client
from app.rag.config import RECIPE_COLLECTION_NAME, DEFAULT_TOP_K, DEFAULT_SCORE_THRESHOLD
from app.rag.embeddings import get_embedding_service


@dataclass
class RecipeSearchResult:
    """A single recipe retrieval result."""

    id: str
    title: str
    ingredients: List[str]
    steps: str
    calories: int
    difficulty: str
    tags: List[str]
    image_url: str
    score: float


def _format_query_for_embedding(query: str, image_url: Optional[str] = None) -> str:
    """Format user query for embedding-based retrieval."""
    context = "推荐合适的菜谱：" if not image_url else "根据图片中的食材推荐菜谱："
    return f"{context}{query}"


def retrieve_recipes(
    query: str,
    image_url: Optional[str] = None,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
) -> List[RecipeSearchResult]:
    """
    Retrieve the most relevant recipes from the knowledge base.

    Args:
        query: User's text query.
        image_url: Optional image URL (used for context only in retrieval).
        top_k: Maximum number of results to return.
        score_threshold: Minimum similarity score for results.

    Returns:
        A list of recipe search results sorted by relevance.
    """
    client = get_qdrant_client()
    embedding_service = get_embedding_service()

    search_text = _format_query_for_embedding(query, image_url)
    query_vector = embedding_service.embed_query(search_text)

    logger.info(f"Retrieving recipes for query: {query[:50]}...")

    response = client.query_points(
        collection_name=RECIPE_COLLECTION_NAME,
        query=query_vector,
        limit=top_k,
        score_threshold=score_threshold,
    )

    results: List[RecipeSearchResult] = []
    for scored_point in response.points:
        payload = scored_point.payload or {}
        results.append(
            RecipeSearchResult(
                id=payload.get("id", str(scored_point.id)),
                title=payload.get("title", ""),
                ingredients=payload.get("ingredients", []),
                steps=payload.get("steps", ""),
                calories=payload.get("calories", 0),
                difficulty=payload.get("difficulty", ""),
                tags=payload.get("tags", []),
                image_url=payload.get("image_url", ""),
                score=scored_point.score,
            )
        )

    logger.info(f"Retrieved {len(results)} recipes")
    return results
