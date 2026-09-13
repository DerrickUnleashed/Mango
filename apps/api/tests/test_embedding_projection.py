"""Unit tests for embedding projection/dimensionality reduction."""

from __future__ import annotations

import numpy as np

from app.services.embedding_projection import (
    _pca_2d,
    project_observations_with_prototypes,
    project_prototypes,
)


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


def test_prototypes_share_observation_embedding_space() -> None:
    """Prototypes embed in the same affine space as the observations.

    With PCA the projection is affine, so projecting a prototype that equals
    the mean of a cluster's observation vectors must land exactly at the mean
    of that cluster's projected points — the centroid overlay sits inside its
    cluster instead of being placed by an independent (meaningless) run.
    """
    rng = np.random.default_rng(11)
    # Three separable clusters of observations.
    clusters = [
        rng.normal([2.0, 0.0, 0.0, 0.0, 0.0, 0.0], scale=0.2, size=(8, 6)),
        rng.normal([0.0, 2.0, 1.0, 0.0, 0.0, 0.0], scale=0.2, size=(8, 6)),
        rng.normal([0.0, 0.0, 0.0, 2.0, 1.0, 0.0], scale=0.2, size=(8, 6)),
    ]
    observations = [list(row) for _, cluster in enumerate(clusters) for row in cluster]
    prototypes = [list(cluster.mean(axis=0)) for cluster in clusters]

    proto_coords, obs_coords, count = project_observations_with_prototypes(
        observations, prototypes, method="pca", max_points=100
    )
    assert count == len(observations)
    assert len(proto_coords) == len(prototypes)
    assert len(obs_coords) == len(observations)

    obs_arr = np.asarray(obs_coords, dtype=float).reshape(len(clusters), 8, 2)
    for i, _centroid in enumerate(prototypes):
        mean_x = float(obs_arr[i, :, 0].mean())
        mean_y = float(obs_arr[i, :, 1].mean())
        assert abs(mean_x - proto_coords[i][0]) < 1e-6
        assert abs(mean_y - proto_coords[i][1]) < 1e-6


def test_prototypes_without_observations_fall_back_to_own_projection() -> None:
    observations: list[list[float]] = []
    prototypes = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [0.0, 0.0]]
    proto_coords, obs_coords, count = project_observations_with_prototypes(
        observations, prototypes, method="pca"
    )
    assert count == 0
    assert obs_coords == []
    assert len(proto_coords) == len(prototypes)


def test_observations_without_prototypes_still_project() -> None:
    observations = [[1.0, 2.0, 3.0], [2.0, 1.0, 1.0], [3.0, 3.0, 0.0]]
    proto_coords, obs_coords, count = project_observations_with_prototypes(
        observations, [], method="pca"
    )
    assert count == len(observations)
    assert proto_coords == []
    assert len(obs_coords) == len(observations)
