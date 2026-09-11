"""Tests for the self-supervised training scaffold."""

from __future__ import annotations

import numpy as np

from orchardvision_ml.identity import Embedding
from orchardvision_ml.identity.training import (
    ContrastiveTrainer,
    PairOptions,
    PairSampler,
    TrainingPair,
)


def _build_trackable_embeddings() -> list[Embedding]:
    """Embeddings from one fruit with occlusion + two spatially separated fruits."""
    track3: list[Embedding] = []
    for frame_id in (5, 6, 8):
        track3.append(
            Embedding(
                track_id=3,
                frame_id=frame_id,
                vector=np.asarray([1.0, 0.0, 0.0], dtype=np.float32),
                bbox=(100.0 + frame_id, 100.0, 30.0, 30.0),
                confidence=0.9,
            )
        )
    track9 = [
        Embedding(
            track_id=9,
            frame_id=7,
            vector=np.asarray([0.0, 1.0, 0.0], dtype=np.float32),
            bbox=(600.0, 100.0, 30.0, 30.0),
            confidence=0.8,
        )
    ]
    track17 = [
        Embedding(
            track_id=17,
            frame_id=7,
            vector=np.asarray([0.0, 0.0, 1.0], dtype=np.float32),
            bbox=(900.0, 100.0, 30.0, 30.0),
            confidence=0.85,
        )
    ]
    return track3 + track9 + track17


def test_pair_sampler_temporal_positives() -> None:
    sampler = PairSampler(PairOptions(max_frames_apart=4))
    pairs = sampler.build(_build_trackable_embeddings())

    with_anchor3 = [p for p in pairs if p.anchor.track_id == 3]
    assert len(with_anchor3) == 3
    for pair in with_anchor3:
        assert pair.positive is not None
        assert pair.positive.track_id == 3
        assert abs(pair.positive.frame_id - pair.anchor.frame_id) <= 4
        assert len(pair.negatives) == 2  # one representative per other tracklet
    assert pairs[0].anchor.frame_id < pairs[1].anchor.frame_id < pairs[2].anchor.frame_id


def test_pair_sampler_hard_negative_mining_keeps_most_similar() -> None:
    sampler = PairSampler(
        PairOptions(max_frames_apart=4, hard_mining_top_k=1, negative_batch_size=2)
    )
    pairs = sampler.build(_build_trackable_embeddings())
    pair = next(p for p in pairs if p.anchor.track_id == 3)
    # With top_k=1 and three negatives available, only the single hardest is kept.
    assert len(pair.negatives) == 1


def test_pair_sampler_filters_occluded() -> None:
    import numpy as np

    embeddings = [
        Embedding(
            track_id=3,
            frame_id=5,
            vector=np.asarray([1.0, 0.0, 0.0], dtype=np.float32),
            bbox=(100.0, 100.0, 30.0, 30.0),
            confidence=0.9,
            is_occluded=True,
        ),
        Embedding(
            track_id=3,
            frame_id=6,
            vector=np.asarray([1.0, 0.0, 0.0], dtype=np.float32),
            bbox=(101.0, 100.0, 30.0, 30.0),
            confidence=0.9,
            is_occluded=False,
        ),
        Embedding(
            track_id=9,
            frame_id=6,
            vector=np.asarray([0.0, 1.0, 0.0], dtype=np.float32),
            bbox=(600.0, 100.0, 30.0, 30.0),
            confidence=0.8,
        ),
    ]
    sampler = PairSampler(PairOptions(max_frames_apart=10, include_occluded=False))
    pairs = sampler.build(embeddings)
    assert all(not p.anchor.is_occluded for p in pairs)
    assert all(not p.anchor.is_occluded and not p.positive.is_occluded for p in pairs if p.positive)

    sampler_include = PairSampler(PairOptions(max_frames_apart=10, include_occluded=True))
    assert any(p.anchor.is_occluded for p in sampler_include.build(embeddings))


def test_pair_sampler_spatial_separation_requires_distance() -> None:
    import numpy as np

    embeddings = [
        Embedding(
            track_id=3,
            frame_id=5,
            vector=np.asarray([1.0, 0.0, 0.0], dtype=np.float32),
            bbox=(100.0, 100.0, 30.0, 30.0),
            confidence=0.9,
        ),
        Embedding(
            track_id=9,
            frame_id=5,
            vector=np.asarray([0.0, 1.0, 0.0], dtype=np.float32),
            bbox=(110.0, 100.0, 30.0, 30.0),
            confidence=0.9,
        ),
    ]
    # 15px separation fails min_center_distance=60 -> drop to dissimilarity pool.
    sampler = PairSampler(PairOptions(min_center_distance=60.0))
    pairs = sampler.build(embeddings)
    assert any(p.negatives for p in pairs)


def test_contrastive_trainer_separates_positives_from_negatives() -> None:
    sampler = PairSampler(PairOptions(max_frames_apart=6))
    pairs = sampler.build(_build_trackable_embeddings())
    assert pairs

    trainer = ContrastiveTrainer(
        feature_dim=3, n_components=2, epochs=200, learning_rate=0.05, temperature=0.5
    )
    result = trainer.train(pairs)

    assert len(result.loss_history) == 200
    assert result.loss_history[-1] <= result.loss_history[0] + 1e-6
    assert result.positive_similarity > result.negative_similarity
    assert result.separation() > 0.0


def test_contrastive_trainer_projection_shape_and_units() -> None:
    trainer = ContrastiveTrainer(feature_dim=3, n_components=2)
    import numpy as np

    vectors = np.random.default_rng(1).standard_normal((4, 3)).astype(np.float32)
    projected = trainer.project(vectors)
    assert projected.shape == (4, 2)
    assert np.allclose(np.linalg.norm(projected, axis=1), 1.0, atol=1e-5)


def test_contrastive_trainer_empty_state_loss() -> None:
    trainer = ContrastiveTrainer(feature_dim=3, n_components=2, epochs=3)
    import numpy as np

    lone = TrainingPair(
        anchor=Embedding(
            track_id=1,
            frame_id=1,
            vector=np.asarray([1.0, 0.0, 0.0], dtype=np.float32),
            bbox=(0.0, 0.0, 10.0, 10.0),
        )
    )
    result = trainer.train([lone])
    assert result.loss_history == [0.0, 0.0, 0.0]
