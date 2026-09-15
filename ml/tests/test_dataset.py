"""Tests for the crop-level tracklet dataset (Stage A)."""

from __future__ import annotations

import numpy as np

from orchardvision_ml.identity.dataset import (
    TrackletDataset,
    TrackletPartitioner,
    TrackObservation,
    crop_observation,
)
from orchardvision_ml.identity.training import PairOptions


def _obs(
    track_id: int,
    frame_id: int,
    bbox: tuple[float, float, float, float],
    confidence: float = 0.9,
    is_occluded: bool = False,
    vector: np.ndarray | None = None,
) -> TrackObservation:
    return TrackObservation(
        track_id=track_id,
        frame_id=frame_id,
        bbox=bbox,
        confidence=confidence,
        is_occluded=is_occluded,
        vector=vector,
    )


def test_partitioner_splits_on_frame_gap() -> None:
    partitioner = TrackletPartitioner(max_frame_gap=5, min_sub_length=2)
    subtracklets = partitioner.partition(
        [
            _obs(1, frame_id=0, bbox=(0, 0, 10, 10)),
            _obs(1, frame_id=1, bbox=(1, 0, 10, 10)),
            _obs(1, frame_id=20, bbox=(2, 0, 10, 10)),
            _obs(1, frame_id=21, bbox=(3, 0, 10, 10)),
        ]
    )
    assert len(subtracklets) == 2
    assert subtracklets[0].first_frame == 0
    assert subtracklets[0].last_frame == 1
    assert subtracklets[1].first_frame == 20
    assert subtracklets[1].last_frame == 21


def test_partitioner_splits_on_confidence_drop() -> None:
    partitioner = TrackletPartitioner(min_confidence=0.5, min_sub_length=2)
    subtracklets = partitioner.partition(
        [
            _obs(1, frame_id=0, bbox=(0, 0, 10, 10), confidence=0.9),
            _obs(1, frame_id=1, bbox=(1, 0, 10, 10), confidence=0.2),
            _obs(1, frame_id=2, bbox=(2, 0, 10, 10), confidence=0.8),
        ]
    )
    assert len(subtracklets) == 1
    assert [obs.frame_id for obs in subtracklets[0].observations] == [0, 2]


def test_partitioner_splits_on_appearance_drop() -> None:
    partitioner = TrackletPartitioner(appearance_drop=0.5, min_sub_length=2)
    subtracklets = partitioner.partition(
        [
            _obs(1, frame_id=0, bbox=(0, 0, 10, 10), vector=np.asarray([1.0, 0.0])),
            _obs(1, frame_id=1, bbox=(1, 0, 10, 10), vector=np.asarray([1.0, 0.0])),
            _obs(
                1,
                frame_id=2,
                bbox=(2, 0, 10, 10),
                vector=np.asarray([-1.0, 0.0]),
            ),
            _obs(
                1,
                frame_id=3,
                bbox=(3, 0, 10, 10),
                vector=np.asarray([-1.0, 0.0]),
            ),
        ]
    )
    # Two appearance clusters despite contiguous frames.
    assert len(subtracklets) == 2
    assert len(subtracklets[0].observations) == 2
    assert len(subtracklets[1].observations) == 2


def test_partitioner_filters_occluded_when_requested() -> None:
    partitioner = TrackletPartitioner(filter_occluded=True, min_sub_length=2)
    subtracklets = partitioner.partition(
        [
            _obs(1, frame_id=0, bbox=(0, 0, 10, 10), is_occluded=True),
            _obs(1, frame_id=1, bbox=(1, 0, 10, 10)),
            _obs(1, frame_id=2, bbox=(2, 0, 10, 10)),
        ]
    )
    assert len(subtracklets) == 1
    assert subtracklets[0].first_frame == 1


def test_dataset_temporal_positives_and_spatial_negatives() -> None:
    from orchardvision_ml.identity.dataset import TrackletPartitioner

    dataset = TrackletDataset(
        [
            _obs(3, frame_id=5, bbox=(100.0, 100.0, 30.0, 30.0)),
            _obs(3, frame_id=6, bbox=(102.0, 100.0, 30.0, 30.0)),
            _obs(3, frame_id=10, bbox=(110.0, 100.0, 30.0, 30.0)),
            _obs(9, frame_id=6, bbox=(600.0, 100.0, 30.0, 30.0)),
            _obs(17, frame_id=6, bbox=(900.0, 100.0, 30.0, 30.0)),
        ],
        pair_options=PairOptions(max_frames_apart=4, min_center_distance=60.0),
        partitioner=TrackletPartitioner(min_sub_length=1),
    )
    pairs = dataset.build_pairs()
    anchors3 = [p for p in pairs if p.anchor.track_id == 3]
    assert len(anchors3) == 3
    for pair in anchors3:
        assert pair.positive is not None
        assert pair.positive.track_id == 3
        assert len(pair.negatives) == 2  # one representative per other tracklet


def test_dataset_visibility_filtering() -> None:
    dataset = TrackletDataset(
        [
            _obs(3, frame_id=5, bbox=(100.0, 100.0, 30.0, 30.0), is_occluded=True),
            _obs(3, frame_id=6, bbox=(102.0, 100.0, 30.0, 30.0)),
            _obs(3, frame_id=7, bbox=(104.0, 100.0, 30.0, 30.0)),
        ],
        pair_options=PairOptions(max_frames_apart=10),
    )
    assert all(not p.anchor.is_occluded for p in dataset.build_pairs())


def test_dataset_build_label_pairs_groups_by_pseudo_label() -> None:
    from orchardvision_ml.identity.dataset import TrackletPartitioner

    observations = [
        _obs(1, frame_id=5, bbox=(100.0, 100.0, 30.0, 30.0)),
        _obs(1, frame_id=6, bbox=(103.0, 100.0, 30.0, 30.0)),
        _obs(2, frame_id=5, bbox=(600.0, 100.0, 30.0, 30.0)),
        _obs(2, frame_id=6, bbox=(603.0, 100.0, 30.0, 30.0)),
        _obs(3, frame_id=5, bbox=(900.0, 100.0, 30.0, 30.0)),
        _obs(3, frame_id=6, bbox=(903.0, 100.0, 30.0, 30.0)),
    ]
    dataset = TrackletDataset(
        observations,
        pair_options=PairOptions(max_frames_apart=4, min_center_distance=60.0),
        partitioner=TrackletPartitioner(min_sub_length=1),
    )
    # Sub-tracklet indices 0..2 (tracks 1, 2, 3). Merge tracks 1 and 3 into one
    # pseudo identity (label 0), keep track 2 separate (label 1).
    labels = {0: 0, 1: 1, 2: 0}
    pairs = dataset.build_label_pairs(labels)

    track1 = [p for p in pairs if p.anchor.track_id == 1]
    # Cross-tracklet positive: track-1 anchors can pair with track-3 obs (same label).
    assert all(p.positive.track_id != 1 for p in track1)
    # Negatives come only from the differing label (track 2); one representative.
    assert all(len(p.negatives) == 1 and p.negatives[0].track_id == 2 for p in track1)


def test_dataset_hard_negative_mining_uses_vectors() -> None:
    from orchardvision_ml.identity.dataset import TrackletPartitioner

    dataset = TrackletDataset(
        [
            _obs(
                3,
                frame_id=5,
                bbox=(100.0, 100.0, 30.0, 30.0),
                vector=np.asarray([1.0, 0.0, 0.0], dtype=np.float32),
            ),
            _obs(
                3,
                frame_id=6,
                bbox=(102.0, 100.0, 30.0, 30.0),
                vector=np.asarray([1.0, 0.0, 0.0], dtype=np.float32),
            ),
            _obs(
                9,
                frame_id=6,
                bbox=(600.0, 100.0, 30.0, 30.0),
                vector=np.asarray([0.0, 1.0, 0.0], dtype=np.float32),
            ),
            _obs(
                17,
                frame_id=6,
                bbox=(900.0, 100.0, 30.0, 30.0),
                vector=np.asarray([0.45, 0.89, 0.0], dtype=np.float32),
            ),
        ],
        pair_options=PairOptions(max_frames_apart=4, hard_mining_top_k=1, negative_batch_size=2),
        partitioner=TrackletPartitioner(min_sub_length=1),
    )
    pairs = dataset.build_pairs()
    pair = next(p for p in pairs if p.anchor.track_id == 3)
    # top_k=1 keeps only the most anchor-similar negative (track 17, cos 0.45).
    assert len(pair.negatives) == 1
    assert pair.negatives[0].track_id == 17


def test_crop_observation_shape_and_normalization() -> None:
    frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
    obs = _obs(1, frame_id=0, bbox=(100.0, 100.0, 80.0, 80.0))
    crop = crop_observation(frame, obs, input_size=112)
    assert crop.shape == (3, 112, 112)
    assert crop.dtype == np.float32
    assert not np.isnan(crop).any()


def test_crop_observation_empty_bbox_fallback() -> None:
    frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
    obs = _obs(1, frame_id=0, bbox=(1000.0, 1000.0, 10.0, 10.0))  # outside frame
    crop = crop_observation(frame, obs, input_size=64)
    assert crop.shape == (3, 64, 64)
