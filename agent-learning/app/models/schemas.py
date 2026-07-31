from typing import Optional, List

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Request model for streaming chat."""

    message: str
    image_url: Optional[str] = None
    thread_id: str
    sources: Optional[List["RecipeSource"]] = None


class RetrieveRequest(BaseModel):
    """Request model for recipe retrieval."""

    query: str
    image_url: Optional[str] = None
    top_k: int = 5


class RecipeSource(BaseModel):
    """A retrieved recipe source returned by the RAG system."""

    id: str
    title: str
    ingredients: List[str]
    steps: str
    calories: int
    difficulty: str
    tags: List[str]
    image_url: str
    score: float


class RetrieveResponse(BaseModel):
    """Response model for recipe retrieval."""

    sources: List[RecipeSource]
    query_time_ms: int


# Forward reference resolution for ChatRequest.sources
ChatRequest.model_rebuild()
