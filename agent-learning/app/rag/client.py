"""Qdrant client and collection management."""

import json
import os
import uuid
from typing import List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from app.common.logger import logger
from app.rag.config import (
    QDRANT_PATH,
    RECIPE_COLLECTION_NAME,
    EMBEDDING_DIMENSION,
    RECIPES_JSON_PATH,
)
from app.rag.embeddings import get_embedding_service


# Namespace for deterministic UUID generation from recipe IDs
RECIPE_ID_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # DNS namespace


def _recipe_id_to_uuid(recipe_id: str) -> str:
    """Convert a recipe string ID to a deterministic UUID."""
    return str(uuid.uuid5(RECIPE_ID_NAMESPACE, recipe_id))


def get_qdrant_client() -> QdrantClient:
    """Get a Qdrant client using local file storage."""
    os.makedirs(QDRANT_PATH, exist_ok=True)
    return QdrantClient(path=QDRANT_PATH)


def _build_document_text(recipe: Dict[str, Any]) -> str:
    """Build the text representation of a recipe for embedding."""
    ingredients = recipe.get("ingredients", [])
    ingredients_text = "\n".join(f"- {ingredient}" for ingredient in ingredients)

    return (
        f"菜名：{recipe.get('title', '')}\n\n"
        f"食材：\n{ingredients_text}\n\n"
        f"做法：\n{recipe.get('steps', '')}\n\n"
        f"标签：{', '.join(recipe.get('tags', []))}"
    )


def _collection_exists(client: QdrantClient) -> bool:
    """Check if the recipe collection already exists."""
    collections = client.get_collections().collections
    return any(collection.name == RECIPE_COLLECTION_NAME for collection in collections)


def _load_recipes() -> List[Dict[str, Any]]:
    """Load recipes from the JSON file."""
    if not os.path.exists(RECIPES_JSON_PATH):
        raise FileNotFoundError(f"Recipes file not found: {RECIPES_JSON_PATH}")

    with open(RECIPES_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _index_recipes(client: QdrantClient, recipes: List[Dict[str, Any]]) -> None:
    """Index recipes into Qdrant."""
    embedding_service = get_embedding_service()

    texts = [_build_document_text(recipe) for recipe in recipes]
    embeddings = embedding_service.embed(texts)

    points: List[PointStruct] = []
    for recipe, embedding in zip(recipes, embeddings):
        points.append(
            PointStruct(
                id=_recipe_id_to_uuid(recipe["id"]),
                vector=embedding,
                payload={
                    "id": recipe["id"],
                    "title": recipe.get("title", ""),
                    "ingredients": recipe.get("ingredients", []),
                    "steps": recipe.get("steps", ""),
                    "calories": recipe.get("calories", 0),
                    "difficulty": recipe.get("difficulty", ""),
                    "tags": recipe.get("tags", []),
                    "image_url": recipe.get("image_url", ""),
                },
            )
        )

    client.upsert(collection_name=RECIPE_COLLECTION_NAME, points=points)
    logger.info(f"Indexed {len(points)} recipes into Qdrant")


def ensure_collection_initialized() -> None:
    """
    Ensure the recipe collection exists and is populated.

    This function is safe to call on application startup:
    - If the collection already exists, it does nothing.
    - If the collection does not exist, it creates it and indexes recipes.
    """
    client = get_qdrant_client()

    if _collection_exists(client):
        logger.info(f"Qdrant collection '{RECIPE_COLLECTION_NAME}' already exists")
        return

    logger.info(f"Creating Qdrant collection '{RECIPE_COLLECTION_NAME}'")
    client.create_collection(
        collection_name=RECIPE_COLLECTION_NAME,
        vectors_config=VectorParams(
            size=EMBEDDING_DIMENSION,
            distance=Distance.COSINE,
        ),
    )

    recipes = _load_recipes()
    _index_recipes(client, recipes)
    logger.info("Recipe knowledge base initialized successfully")
