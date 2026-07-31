"""RAG module configuration."""

import os

# Qdrant configuration
QDRANT_PATH = os.getenv("QDRANT_PATH", "db/qdrant")
RECIPE_COLLECTION_NAME = "recipes"

# Embedding configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")
EMBEDDING_DIMENSION = 1024
EMBEDDING_BATCH_SIZE = 8

# Retrieval configuration
DEFAULT_TOP_K = 5
DEFAULT_SCORE_THRESHOLD = 0.0

# Data source
RECIPES_JSON_PATH = os.getenv("RECIPES_JSON_PATH", "resource/recipes.json")
