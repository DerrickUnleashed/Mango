"""Non-maximum suppression (NMS) for detection post-processing.

Pure-numpy implementation so it can be tested (and used standalone) without a
model backend; the YOLO adapter applies it after raw model output.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    """Intersection-over-union for two boxes in ``[x, y, width, height]`` form."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0.0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    if inter <= 0.0:
        return 0.0
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0.0 else 0.0


def nms(
    boxes: Sequence[tuple[float, float, float, float]],
    scores: Sequence[float],
    iou_threshold: float = 0.45,
) -> list[int]:
    """Greedy non-maximum suppression.

    Args:
        boxes: ``[x, y, width, height]`` boxes.
        scores: Per-box confidence scores.
        iou_threshold: Boxes overlapping above this IoU with a higher-scoring
            candidate are suppressed.

    Returns:
        Indices (into the input lists) of the boxes kept after suppression.
    """
    if len(boxes) == 0:
        return []
    order = np.argsort(-np.asarray(scores, dtype=float))
    kept: list[int] = []
    suppressed = np.zeros(len(boxes), dtype=bool)
    for idx in order.tolist():
        if suppressed[int(idx)]:
            continue
        kept.append(int(idx))
        for jdx in order.tolist():
            if int(jdx) == int(idx) or suppressed[int(jdx)]:
                continue
            if iou(boxes[int(idx)], boxes[int(jdx)]) > iou_threshold:
                suppressed[int(jdx)] = True
    return kept


def filter_by_class(
    class_labels: Sequence[str],
    allowed: set[str] | None = None,
) -> list[bool]:
    """Per-box keep mask for the requested class labels."""
    if allowed is None:
        return [True] * len(class_labels)
    return [label in allowed for label in class_labels]
