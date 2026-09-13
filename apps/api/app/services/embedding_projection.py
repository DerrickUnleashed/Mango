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


def project_prototypes(
    vectors: Sequence[Sequence[float]],
    method: str = "tsne",
) -> list[tuple[float, float]]:
    """Project embedding vectors to 2D coordinates.

    ``method`` may be ``"tsne"`` (sklearn, when importable), ``"umap"``
    (umap-learn, when importable), or ``"pca"``. Unavailable non-linear
    methods degrade to ``"pca"``.
    """
    if not vectors:
        return []
    data = np.asarray(vectors, dtype=float).reshape(len(vectors), -1)
    if len(data) < 3:
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
