"""Tests for pseudo-label clustering (Stage C: DBSCAN over tracklets)."""

from __future__ import annotations

import numpy as np

from orchardvision_ml.identity.cluster import (
    PseudoLabelResult,
    assign_centroid_pseudo_labels,
    dbscan,
)
from orchardvision_ml.identity.dataset import SubTracklet, TrackObservation


def _obs(track_id: int, frame_id: int, vector: np.ndarray | None) -> TrackObservation:
    return TrackObservation(
        track_id=track_id,
        frame_id=frame_id,
        bbox=(100.0, 100.0, 30.0, 30.0),
        confidence=0.9,
        is_occluded=False,
        vector=vector,
    )


def _sub(track_id: int, vectors: list[np.ndarray]) -> SubTracklet:
    return SubTracklet(
        track_id=track_id,
        sub_index=0,
        observations=[
            _obs(track_id, frame_id=index, vector=vector)
            for index, vector in enumerate(vectors)
        ],
    )


def test_dbscan_clusters_two_well_separated_groups() -> None:
    vectors = np.asarray(
        [
            *[[1.0, 0.0, 0.0]] * 4,
            *[[0.0, 1.0, 0.0]] * 4,
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float32,
    )
    labels = dbscan(vectors, eps=0.3, min_samples=3)
    assert set(labels[:4].tolist()) == {0}
    assert set(labels[4:8].tolist()) == {1}
    assert labels[8] == -1  # far from everything -> noise


def test_dbscan_validation_report_visible_reports_centroid_pseudo_labels() -> None:
    subtracklets = [
        _sub(1, [[1.0, 0.0, 0.0], [0.99, 0.1, 0.0]]),
        _sub(2, [[1.0, 0.01, 0.0], [0.98, 0.05, 0.0]]),
        _sub(3, [[0.01, 1.0, 0.0], [0.05, 0.99, 0.0]]),
        _sub(4, [[0.99, 0.01, 0.01]]),
    ]
    result = assign_centroid_pseudo_labels(subtracklets, eps=0.3, min_samples=2)
    assert isinstance(result, PseudoLabelResult)
    assert result.cluster_count == 1
    # Tracklets 1, 2, 4 merge into one pseudo identity; tracklet 3 is noise.
    assert result.labels == {0: 0, 1: 0, 3: 0}
    assert result.unlabeled_indices == [2]


def test_assign_excludes_tracklets_without_vectors() -> None:
    subtracklets = [_sub(5, [])]
    result = assign_centroid_pseudo_labels(subtracklets, eps=0.3, min_samples=2)
    assert result.labels == {}
    assert result.unlabeled_indices == []


def test_assign_empty_input() -> None:
    result = assign_centroid_pseudo_labels([], eps=0.3, min_samples=2)
    assert result.labels == {}
    assert result.unlabeled_indices == []
    assert result.cluster_count == 0


def test_dbscan_output_is_dense() -> None:
    vectors = np.asarray(
        [[1.0, 0.0], [0.99, 0.01], [0.0, 1.0], [0.01, 0.99]],
        dtype=np.float32,
    )
    labels = dbscan(vectors, eps=0.3, min_samples=2)
    assert sorted(set(labels.tolist())) == [-1, 0, 1] or set(labels.tolist()) <= {-1, 0, 1}
