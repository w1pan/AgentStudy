"""RAG (Retrieval-Augmented Generation) module for recipe knowledge base."""

from app.rag.retriever import retrieve_recipes, RecipeSearchResult
from app.rag.client import ensure_collection_initialized

__all__ = ["retrieve_recipes", "RecipeSearchResult", "ensure_collection_initialized"]
