"""Dimensionality reduction for embedding visualization.

Projects embedding vectors to 2D using t-SNE (sklearn) or UMAP
(umap-learn) when available, and always falls back to PCA via numpy SVD so
the stack has no hard dependency on either library. Outputs are always
deterministic.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import numpy as np

logger = logging.getLogger(__name__)


def _pca_2d(vectors: np.ndarray) -> np.ndarray:
    """Project rows onto the top-2 principal components (numpy SVD)."""
    centered = vectors - vectors.mean(axis=0, keepdims=True)
    u, s, vt = np.linalg.svd(centered, full_matrices=False)
    coords = u[:, :2] * s[:2]
    scale = np.max(np.abs(coords)) if coords.size else 1.0
    if scale == 0.0:
        scale = 1.0
    return coords / scale


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float | None:
    """Cosine similarity between two vectors, or ``None`` on degenerate input."""
    if not a or not b or len(a) != len(b):
        return None
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = np.sqrt(sum(x * x for x in a))
    norm_b = np.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return None
    return round(float(dot / (norm_a * norm_b)), 4)


def _ring_layout(vectors: np.ndarray) -> np.ndarray:
    """Deterministic placement when there are too few points for PCA."""
    n = len(vectors)
    if n == 1:
        return np.zeros((1, 2), dtype=float)
    angles = 2.0 * np.pi * np.arange(n) / n
    return np.column_stack([np.cos(angles), np.sin(angles)])


def _normalized_coords(coords: np.ndarray) -> list[tuple[float, float]]:
    """Scale coordinates to the [-1, 1] box so all methods share one range."""
    scale = np.max(np.abs(coords)) if coords.size else 1.0
    if scale == 0.0:
        scale = 1.0
    return [(float(x / scale), float(y / scale)) for x, y in coords]


def _tsne_2d(data: np.ndarray) -> np.ndarray | None:
    """Project via t-SNE (sklearn), or ``None`` when unavailable/failed."""
    try:
        from sklearn.manifold import TSNE  # type: ignore[import-not-found]

        perplexity = min(30.0, max(2.0, len(data) - 1))
        return TSNE(
            n_components=2,
            perplexity=perplexity,
            init="pca",
            random_state=0,
        ).fit_transform(data)
    except ImportError:
        return None
    except Exception:
        logger.warning("t-SNE projection failed", exc_info=True)
        return None


def _umap_2d(data: np.ndarray) -> np.ndarray | None:
    """Project via UMAP (umap-learn), or ``None`` when unavailable/failed."""
    try:
        import umap  # type: ignore[import-not-found]

        return umap.UMAP(n_components=2, random_state=0).fit_transform(data)
    except ImportError:
        logger.warning("umap-learn not installed; falling back")
        return None
    except Exception:
        logger.warning("UMAP projection failed", exc_info=True)
        return None


def _project(
    vectors: Sequence[Sequence[float]] | np.ndarray, method: str
) -> list[tuple[float, float]]:
    """Project ``vectors`` to 2D via ``method``, always normalized to [-1, 1].

    ``method`` may be ``"tsne"`` (sklearn, when importable), ``"umap"``
    (umap-learn, when importable), or ``"pca"``. Unavailable non-linear
    methods degrade to ``"pca"``.
    """
    if len(vectors) == 0:
        return []
    data = np.asarray(vectors, dtype=float).reshape(len(vectors), -1)
    if data.shape[0] < 3:
        coords = _ring_layout(data)
        return [(float(x), float(y)) for x, y in coords]

    if method == "tsne":
        coords = _tsne_2d(data)
    elif method == "umap":
        coords = _umap_2d(data)
    else:
        coords = None
    if coords is not None:
        return _normalized_coords(coords)

    coords = _pca_2d(data)
    return [(float(x), float(y)) for x, y in coords]


def _sample_vectors(vectors: Sequence[Sequence[float]], max_points: int) -> list[Sequence[float]]:
    """Deterministically subsample ``vectors`` to at most ``max_points``."""
    if len(vectors) <= max_points:
        return list(vectors)
    step = len(vectors) / max_points
    return [vectors[int(i * step)] for i in range(max_points)]


def project_prototypes(
    vectors: Sequence[Sequence[float]],
    method: str = "tsne",
) -> list[tuple[float, float]]:
    """Project embedding vectors to 2D coordinates."""
    return _project(vectors, method)


def project_observations_with_prototypes(
    observation_vectors: Sequence[Sequence[float]],
    prototype_vectors: Sequence[Sequence[float]],
    method: str = "tsne",
    max_points: int = 500,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]], int]:
    """Project observations and identity prototypes in one shared space.

    Stacks the prototype vectors on top of the deterministically sampled
    observation vectors, runs a single projection, and returns the split
    coordinates. Because the prototypes are embedded in the same run as the
    observations, centroid overlays land inside their identity clusters.
    **Callers must use the same ``observation_vectors`` and ``max_points``**
    so separate requests agree; every method uses a fixed random seed.
    """
    observations = _sample_vectors(observation_vectors, max_points)
    if not prototype_vectors:
        return [], _project(observations, method), len(observations)
    if not observations:
        return _project(prototype_vectors, method), [], 0

    data = np.vstack(
        [np.asarray(prototype_vectors, dtype=float), np.asarray(observations, dtype=float)]
    )
    coords = _project(data, method)
    split = len(prototype_vectors)
    return coords[:split], coords[split:], len(observations)
