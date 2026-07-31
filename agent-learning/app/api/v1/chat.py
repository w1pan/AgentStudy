import time
from typing import List

from fastapi import APIRouter
from app.models.schemas import ChatRequest, RetrieveRequest, RetrieveResponse, RecipeSource
from fastapi.responses import StreamingResponse
from app.agents.personal_chief import search_recipes, get_messages, clear_messages, retrieve_recipes_for_query
from app.rag.retriever import RecipeSearchResult

router = APIRouter()


def _to_recipe_source(result: RecipeSearchResult) -> RecipeSource:
    """Convert a retrieval result to a Pydantic response model."""
    return RecipeSource(
        id=result.id,
        title=result.title,
        ingredients=result.ingredients,
        steps=result.steps,
        calories=result.calories,
        difficulty=result.difficulty,
        tags=result.tags,
        image_url=result.image_url,
        score=result.score,
    )


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_endpoint(request: RetrieveRequest):
    """Retrieve relevant recipes from the knowledge base."""
    start_time = time.perf_counter()

    results = retrieve_recipes_for_query(
        query=request.query,
        image_url=request.image_url,
        top_k=request.top_k,
    )

    elapsed_ms = int((time.perf_counter() - start_time) * 1000)

    return RetrieveResponse(
        sources=[_to_recipe_source(result) for result in results],
        query_time_ms=elapsed_ms,
    )


@router.post("/chat/stream")
async def chat_endpoint(request: ChatRequest):
    """流式对话，可传入已检索好的 sources。"""
    sources = None
    if request.sources:
        sources = [
            RecipeSearchResult(
                id=source.id,
                title=source.title,
                ingredients=source.ingredients,
                steps=source.steps,
                calories=source.calories,
                difficulty=source.difficulty,
                tags=source.tags,
                image_url=source.image_url,
                score=source.score,
            )
            for source in request.sources
        ]

    return StreamingResponse(
        search_recipes(request.message, request.image_url, request.thread_id, sources=sources),
        media_type="text/event-stream",
    )


@router.get("/chat/messages")
async def get_chat_messages(thread_id: str):
    """获取历史消息"""
    messages = get_messages(thread_id)
    return {"messages": messages}


@router.delete("/chat/messages")
async def clear_chat_messages(thread_id: str):
    """清空历史消息"""
    clear_messages(thread_id)
    return {"success": True}
