"""Unit tests for embedding projection/dimensionality reduction."""

from __future__ import annotations

import numpy as np

from app.services.embedding_projection import _pca_2d, project_prototypes


def test_project_prototypes_empty() -> None:
    assert project_prototypes([]) == []


def test_project_prototypes_single_point() -> None:
    coords = project_prototypes([[0.5, 0.5, 0.5]])
    assert len(coords) == 1
    x, y = coords[0]
    assert x == 0.0
    assert y == 0.0


def test_project_prototypes_two_points_use_ring_layout() -> None:
    coords = project_prototypes([[1.0, 0.0], [0.0, 1.0]], method="pca")
    assert len(coords) == 2
    for x, y in coords:
        assert round(x * x + y * y, 6) == 1.0


def test_project_prototypes_pca_normalized() -> None:
    rng = np.random.default_rng(7)
    vectors = rng.normal(size=(6, 16)).tolist()
    coords = project_prototypes(vectors, method="pca")
    values = np.asarray(coords, dtype=float)
    assert values.shape == (6, 2)
    assert np.max(np.abs(values)) <= 1.0 + 1e-9


def test_project_prototypes_pca_is_deterministic() -> None:
    vectors = [[1.0, 2.0, 3.0], [2.0, 1.0, 1.0], [3.0, 3.0, 0.0], [0.5, 0.5, 2.0]]
    first = project_prototypes(vectors, method="pca")
    second = project_prototypes(vectors, method="pca")
    assert first == second


def test_project_prototypes_umap_falls_back_when_unavailable() -> None:
    """UMAP must degrade gracefully (returns coords) even without umap-learn."""
    vectors = [
        [1.0, 2.0, 3.0],
        [2.0, 1.0, 1.0],
        [3.0, 3.0, 0.0],
        [0.5, 0.5, 2.0],
        [1.5, 2.5, 1.5],
        [2.5, 0.5, 2.5],
    ]
    for method in ("tsne", "umap"):
        coords = project_prototypes(vectors, method=method)
        assert len(coords) == len(vectors)
        values = np.asarray(coords, dtype=float)
        assert np.max(np.abs(values)) <= 1.0 + 1e-9, method
        for x, y in coords:
            assert isinstance(x, float)
            assert isinstance(y, float)


def test_pca_2d_handles_constant_rows() -> None:
    coords = _pca_2d(np.zeros((4, 8), dtype=float))
    assert coords.shape == (4, 2)
    assert not np.any(np.isnan(coords))
