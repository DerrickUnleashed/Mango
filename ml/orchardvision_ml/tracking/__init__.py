"""Short-term multi-object tracking module.

Public interface: :class:`Tracker`, :class:`Track`, :class:`TrackResult`,
:class:`TrackPoint`, and the association helpers.
Concrete implementations: :class:`MockTracker` (deterministic, offline) and
:class:`ByteTrackAdapter` (ByteTrack-style two-stage association with a
Kalman filter.
"""

from .base import (
    Track,
    Tracker,
    TrackPoint,
    TrackResult,
    associate_by_center_distance,
)
from .bytetrack_adapter import ByteTrackAdapter
from .kalman import KalmanBoxFilter, to_tlwh, to_xyah
from .mock import MockTracker

__all__ = [
    "ByteTrackAdapter",
    "KalmanBoxFilter",
    "MockTracker",
    "Track",
    "TrackPoint",
    "TrackResult",
    "Tracker",
    "associate_by_center_distance",
    "to_tlwh",
    "to_xyah",
]
