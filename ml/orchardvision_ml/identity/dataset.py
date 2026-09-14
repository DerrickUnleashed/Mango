"""Crop-level tracklet dataset for identity embedding training.

Bridges the model-agnostic pairing recipe in :mod:`training` and real video
crops. A ``TrackletDataset`` groups per-frame detections into short-term
tracks, filters them through a noise-filtered tracklet partition (splitting on
frame gaps, confidence drops, and — when embeddings are supplied — appearance
discontinuities), and builds positive/negative observation pairs using the same
temporal/spatial/visibility/hard-mining semantics as
``training.PairSampler`` but operating on croppable observations instead of
already-embedded vectors.

The dataset is dependency-free (numpy + cv2); torch is only required by the
trainer when it fetches crops via :func:`crop_observation`.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import cv2
import numpy as np
from numpy.typing import NDArray

from .base import cosine_similarity
from .torch_extractor import IMAGENET_MEAN, IMAGENET_STD
from .training import PairOptions

if TYPE_CHECKING:
    from .base import Embedding

__all__ = [
    "CropPair",
    "SubTracklet",
    "TrackObservation",
    "TrackletDataset",
    "TrackletPartitioner",
    "crop_observation",
]

_NO_LABEL = object()


@dataclass(frozen=True, slots=True)
class TrackObservation:
    """A single croppable detection belonging to a short-term track.

    Attributes:
        track_id: Short-term track the detection belongs to.
        frame_id: Zero-based frame index.
        bbox: Detection bounding box ``(x, y, w, h)`` in pixel coordinates.
        confidence: Detection confidence in ``[0, 1]``.
        is_occluded: Whether the object was inside a mock occlusion window.
        source_id: Identifies the video this observation came from (used by the
            frame provider to resolve the actual frame).
        vector: Optional current-model embedding; when present it is used to
            rank hard negatives.
    """

    track_id: int
    frame_id: int
    bbox: tuple[float, float, float, float]
    confidence: float = 0.0
    is_occluded: bool = False
    source_id: str = ""
    vector: NDArray[np.float32] | None = None

    @property
    def center(self) -> tuple[float, float]:
        x, y, w, h = self.bbox
        return (x + w / 2.0, y + h / 2.0)


@dataclass(frozen=True, slots=True)
class SubTracklet:
    """A clean, continuous segment of a track after noise filtering.

    Observations are ordered by frame id. Sub-tracklets are the self-supervised
    pseudo-label unit: observations within one sub-tracklet are positives, and
    observations across different sub-tracklets/tracklets are negatives.
    """

    track_id: int
    sub_index: int
    observations: tuple[TrackObservation, ...]

    @property
    def first_frame(self) -> int:
        return self.observations[0].frame_id

    @property
    def last_frame(self) -> int:
        return self.observations[-1].frame_id

    @property
    def length(self) -> int:
        return len(self.observations)

    @property
    def is_confident(self) -> bool:
        """Whether every observation passes the visibility gate."""
        return all(not obs.is_occluded and obs.confidence > 0.0 for obs in self.observations)


@dataclass(frozen=True, slots=True)
class CropPair:
    """Positive/negative observation pair ready for crop-based training.

    Field names mirror :class:`~training.TrainingPair` so the semantic mapping
    between the two scenarios stays explicit; the anchor is always a visible
    observation.
    """

    anchor: TrackObservation
    positive: TrackObservation | None = None
    negatives: list[TrackObservation] = field(default_factory=list)


def crop_observation(
    frame: NDArray[np.uint8],
    observation: TrackObservation,
    input_size: int = 224,
    mean: tuple[float, float, float] | None = None,
    std: tuple[float, float, float] | None = None,
) -> NDArray:
    """Crop a detection from a BGR frame and normalize it for a torch backbone.

    Returns an ``(3, input_size, input_size)`` float32 array using the same
    ImageNet normalization as :class:`~torch_extractor.TorchEmbeddingExtractor`
    (BGR input, RGB output).
    """
    h, w = frame.shape[:2]
    x, y, bw, bh = observation.bbox
    x0, y0 = max(0, int(x)), max(0, int(y))
    x1, y1 = min(w, int(x + bw)), min(h, int(y + bh))
    crop = frame[y0:y1, x0:x1]
    if crop.size == 0:
        mid_y, mid_x = h // 2, w // 2
        crop = frame[max(0, mid_y - 32) : mid_y + 32, max(0, mid_x - 32) : mid_x + 32]
    resized = cv2.resize(crop, (input_size, input_size), interpolation=cv2.INTER_LINEAR)
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    mean_ = np.asarray(mean or IMAGENET_MEAN, np.float32)
    std_ = np.asarray(std or IMAGENET_STD, np.float32)
    rgb = (rgb - mean_) / std_
    return rgb.transpose(2, 0, 1)


class TrackletPartitioner:
    """Noise-filtered tracklet partition (NFTP-style splitting).

    Splits a sorted observation sequence of one track into clean sub-tracklets
    on: frame gaps beyond ``max_frame_gap``, observations below
    ``min_confidence`` (or occluded, when ``filter_occluded``), and — when
    embeddings are available — consecutive-appearance drops beyond
    ``appearance_drop`` (measured as cosine similarity). Segments shorter than
    ``min_sub_length`` are discarded.
    """

    def __init__(
        self,
        max_frame_gap: int = 10,
        min_confidence: float = 0.0,
        filter_occluded: bool = False,
        appearance_drop: float | None = 0.6,
        min_sub_length: int = 2,
    ) -> None:
        self.max_frame_gap = max_frame_gap
        self.min_confidence = min_confidence
        self.filter_occluded = filter_occluded
        self.appearance_drop = appearance_drop
        self.min_sub_length = min_sub_length

    def partition(self, observations: Sequence[TrackObservation]) -> list[SubTracklet]:
        clean = [
            obs
            for obs in observations
            if obs.confidence >= self.min_confidence
            and (not self.filter_occluded or not obs.is_occluded)
        ]
        clean.sort(key=lambda obs: obs.frame_id)
        segments: list[list[TrackObservation]] = [[]]
        prev: TrackObservation | None = None
        for obs in clean:
            if prev is not None and self._breaks_continuity(prev, obs):
                if segments[-1]:
                    segments.append([])
            segments[-1].append(obs)
            prev = obs
        if not segments[-1]:
            segments.pop()

        subtracklets: list[SubTracklet] = []
        for segment in segments:
            if len(segment) < self.min_sub_length:
                continue
            subtracklets.append(
                SubTracklet(
                    track_id=segment[0].track_id,
                    sub_index=len(subtracklets),
                    observations=tuple(segment),
                )
            )
        return subtracklets

    def _breaks_continuity(self, prev: TrackObservation, current: TrackObservation) -> bool:
        if current.frame_id - prev.frame_id > self.max_frame_gap:
            return True
        if (
            self.appearance_drop is not None
            and prev.vector is not None
            and current.vector is not None
            and cosine_similarity(prev.vector, current.vector) < self.appearance_drop
        ):
            return True
        return False


class TrackletDataset:
    """Groups per-frame observations into tracks and builds training pairs.

    Args:
        observations: All observations across the training corpus.
        pair_options: Pair construction semantics (temporal/spatial windows,
            visibility filter, hard-negative mining). Defaults to
            :class:`PairOptions`.
        partitioner: Tracklet partitioner used to derive pseudo-labels.
            Defaults to :class:`TrackletPartitioner`.
        source_of: Optional callable resolving a ``source_id`` — unused during
            pair construction (kept for the trainer to fetch frames lazily).
    """

    def __init__(
        self,
        observations: Sequence[TrackObservation],
        pair_options: PairOptions | None = None,
        partitioner: TrackletPartitioner | None = None,
        source_of: Callable[[str], object] | None = None,
    ) -> None:
        self.options = pair_options or PairOptions()
        self.partitioner = partitioner or TrackletPartitioner()
        self.source_of = source_of or (lambda source_id: source_id)
        self.subtracklets = self._group_tracks(observations)

    def _group_tracks(self, observations: Sequence[TrackObservation]) -> list[SubTracklet]:
        tracks: dict[int, list[TrackObservation]] = {}
        for obs in observations:
            tracks.setdefault(obs.track_id, []).append(obs)
        subtracklets: list[SubTracklet] = []
        for track_id in sorted(tracks):
            subtracklets.extend(self.partitioner.partition(tracks[track_id]))
        return subtracklets

    @property
    def visible_observations(self) -> list[TrackObservation]:
        if self.options.include_occluded:
            return [
                obs for sub in self.subtracklets for obs in sub.observations if obs.confidence > 0.0
            ]
        return [
            obs
            for sub in self.subtracklets
            for obs in sub.observations
            if not obs.is_occluded and obs.confidence > 0.0
        ]

    def build_pairs(self) -> list[CropPair]:
        """Build one :class:`CropPair` per visible anchor observation.

        Positives come from the anchor's own sub-tracklet within the temporal
        window; negatives are drawn from other sub-tracklets that satisfy the
        spatial separation gate, ranked by embedding similarity when available
        (hard-negative mining). Identity is the raw tracker ``track_id``.
        """
        return self._build_pairs(lambda obs: obs.track_id)

    def build_label_pairs(self, labels: Mapping[int, int]) -> list[CropPair]:
        """Build pairs keyed by pseudo-label assignments.

        ``labels`` maps a sub-tracklet index (position in ``self.subtracklets``)
        to a pseudo identity label. Observations from sub-tracklets absent from
        ``labels`` are excluded as anchors (self-paced filtering) but still rank
        as negatives when their label differs.

        Args:
            labels: Sub-tracklet index → pseudo-label mapping.

        Returns:
            One :class:`CropPair` per visible, labeled anchor observation.
        """
        label_of: dict[int, int] = {}
        for index, sub in enumerate(self.subtracklets):
            if index not in labels:
                continue
            for obs in sub.observations:
                label_of[id(obs)] = labels[index]
        return self._build_pairs(lambda obs: label_of.get(id(obs), _NO_LABEL))

    def _build_pairs(self, key_of: Callable[[TrackObservation], object]) -> list[CropPair]:
        visible = self.visible_observations
        by_sub: dict[int, SubTracklet] = {}
        for index, sub in enumerate(self.subtracklets):
            by_sub[index] = sub

        pairs: list[CropPair] = []
        for anchor in visible:
            key = key_of(anchor)
            if key is None or key == _NO_LABEL:
                continue
            positive = self._temporal_positive_by_key(anchor, visible, key_of, key)
            negatives = self._hard_negatives(anchor, visible, by_sub, key_of, key)
            pairs.append(CropPair(anchor=anchor, positive=positive, negatives=negatives))
        return pairs

    def _temporal_positive_by_key(
        self,
        anchor: TrackObservation,
        visible: list[TrackObservation],
        key_of: Callable[[TrackObservation], object],
        key: object,
    ) -> TrackObservation | None:
        candidates = [
            obs
            for obs in visible
            if obs is not anchor
            and key_of(obs) == key
            and abs(obs.frame_id - anchor.frame_id) <= self.options.max_frames_apart
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda obs: abs(obs.frame_id - anchor.frame_id))

    def _center_distance(self, a: TrackObservation, b: TrackObservation) -> float:
        ca, cb = a.center, b.center
        return float(np.hypot(ca[0] - cb[0], ca[1] - cb[1]))

    def _hard_negatives(
        self,
        anchor: TrackObservation,
        visible: list[TrackObservation],
        by_sub: dict[int, SubTracklet],
        key_of: Callable[[TrackObservation], object],
        key: object,
    ) -> list[TrackObservation]:
        pool: list[TrackObservation] = []
        for _sub_index, sub in by_sub.items():
            if key_of(sub.observations[0]) == key:
                continue
            if any(
                self._center_distance(anchor, obs) >= self.options.min_center_distance
                for obs in sub.observations
            ):
                pool.append(sub.observations[0])

        if not pool:
            pool = [obs for obs in visible if obs is not anchor and key_of(obs) != key]

        if all(obs.vector is None for obs in pool):
            rng = np.random.default_rng(seed=hash(anchor.frame_id) & 0xFFFF)
            rng.shuffle(pool)
            hard = list(pool)
        else:
            hard = sorted(
                pool,
                key=lambda obs: (
                    cosine_similarity(anchor.vector, obs.vector)
                    if anchor.vector is not None and obs.vector is not None
                    else -1.0
                ),
                reverse=True,
            )

        hard = hard[: self.options.hard_mining_top_k]
        if len(hard) <= self.options.negative_batch_size:
            return hard
        rng = np.random.default_rng(seed=hash(anchor.frame_id) & 0xFFFF)
        return [
            hard[i]
            for i in rng.choice(
                len(hard), size=self.options.negative_batch_size, replace=False
            ).tolist()
        ]


def as_track_observations(
    embeddings: Sequence[Embedding], source_id: str = ""
) -> list[TrackObservation]:
    """Convert pipeline :class:`~base.Embedding` objects to observations.

    Convenience bridge for feeding persisted identity observations (which carry
    ``track_id``, ``frame_id``, ``bbox``, and an embedding ``vector``) straight
    into a :class:`TrackletDataset`.
    """
    return [
        TrackObservation(
            track_id=emb.track_id,
            frame_id=emb.frame_id,
            bbox=emb.bbox or (0.0, 0.0, 0.0, 0.0),
            confidence=emb.confidence,
            is_occluded=emb.is_occluded,
            source_id=source_id,
            vector=emb.vector,
        )
        for emb in embeddings
        if emb.track_id is not None
    ]
