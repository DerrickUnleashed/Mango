"""Identity embedding extractors."""

from .base import Embedding, EmbeddingExtractor, cosine_similarity
from .mock import EMBEDDING_DIM, MockEmbeddingExtractor
from .torch_extractor import TorchEmbeddingExtractor

__all__ = [
    "EMBEDDING_DIM",
    "Embedding",
    "EmbeddingExtractor",
    "MockEmbeddingExtractor",
    "TorchEmbeddingExtractor",
    "cosine_similarity",
]
