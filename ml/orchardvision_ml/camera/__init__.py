"""Video source package.

Public interface: :class:`VideoSource` and :class:`VideoInfo`.
Concrete implementations: :class:`OpenCVVideoSource` (real footage) and the
synthetic renderer (:class:`SyntheticVideoSource` / :class:`SyntheticScene`) for
offline development and testing.
"""

from .opencv import OpenCVVideoSource
from .synthetic import SyntheticFruit, SyntheticScene, SyntheticVideoSource, default_scene
from .video import VideoInfo, VideoSource

__all__ = [
    "OpenCVVideoSource",
    "SyntheticFruit",
    "SyntheticScene",
    "SyntheticVideoSource",
    "VideoInfo",
    "VideoSource",
    "default_scene",
]
