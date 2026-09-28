"""Dimensionality reduction for identity prototype embeddings.

Uses sklearn t-SNE when available and falls back to PCA via numpy SVD so the
stack has no hard dependency on sklearn. Outputs are always deterministic.
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


def project_prototypes(
    vectors: Sequence[Sequence[float]],
    method: str = "tsne",
) -> list[tuple[float, float]]:
    """Project identity prototype embeddings to 2D coordinates.

    ``method`` may be ``"tsne"`` (sklearn, when importable) or ``"pca"``.
    """
    if not vectors:
        return []
    data = np.asarray(vectors, dtype=float).reshape(len(vectors), -1)
    if len(data) < 3:
        coords = _ring_layout(data)
        return [(float(x), float(y)) for x, y in coords]

    if method == "tsne":
        try:
            from sklearn.manifold import TSNE

            perplexity = min(30.0, max(2.0, len(data) - 1))
            coords = TSNE(
                n_components=2,
                perplexity=perplexity,
                init="pca",
                random_state=0,
            ).fit_transform(data)
            return [(float(x), float(y)) for x, y in coords]
        except ImportError:
            pass
        except Exception:
            logger.warning("t-SNE projection failed; falling back to PCA", exc_info=True)

    coords = _pca_2d(data)
    return [(float(x), float(y)) for x, y in coords]
