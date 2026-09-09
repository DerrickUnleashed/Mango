"""Identity embedding extractors."""

from .base import Embedding, EmbeddingExtractor, cosine_similarity
from .mock import EMBEDDING_DIM, MockEmbeddingExtractor

__all__ = [
    "EMBEDDING_DIM",
    "Embedding",
    "EmbeddingExtractor",
    "MockEmbeddingExtractor",
    "cosine_similarity",
]
