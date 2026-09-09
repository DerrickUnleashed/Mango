"""Ground-truth and predicted trajectory types for evaluation."""

from __future__ import annotations

from dataclasses import dataclass

BBox = tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class Tracklet:
    """A sequence of observations belonging to one object.

    ``object_id`` is the ground-truth identity (or predicted track id,
    depending on which side of a comparison the tracklet belongs to).
    """

    object_id: int
    observations: tuple[tuple[int, BBox], ...]

    @property
    def frames(self) -> frozenset[int]:
        return frozenset(frame for frame, _ in self.observations)

    def bbox_at(self, frame: int) -> BBox | None:
        for f, bbox in self.observations:
            if f == frame:
                return bbox
        return None

    def __len__(self) -> int:
        return len(self.observations)


def iou(a: BBox, b: BBox) -> float:
    """Intersection-over-union of two axis-aligned boxes ``(x, y, w, h)``."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ax1, ay1 = ax + aw, ay + ah
    bx1, by1 = bx + bw, by + bh

    ix1, iy1 = max(ax, bx), max(ay, by)
    ix2, iy2 = min(ax1, bx1), min(ay1, by1)
    iw, ih = ix2 - ix1, iy2 - iy1
    if iw <= 0 or ih <= 0:
        return 0.0

    inter = iw * ih
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0
