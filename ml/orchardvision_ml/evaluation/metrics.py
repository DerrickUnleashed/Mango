"""Tracking and identity metrics for the evaluation harness.

Metrics operate on ground-truth and predicted :class:`Tracklet` sequences so
they stay decoupled from any single tracker or re-id implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush

from .tracks import Tracklet, iou

IOU_MATCH = 0.5


def _frame_box_index(tracklets: list[Tracklet]) -> dict[int, dict[int, tuple]]:
    """Map ``frame -> object_id -> bbox`` for sparse lookup."""
    index: dict[int, dict[int, tuple]] = {}
    for track in tracklets:
        for frame, bbox in track.observations:
            index.setdefault(frame, {})[track.object_id] = bbox
    return index


def _assignment_matrix(gt: list[Tracklet], pred: list[Tracklet]) -> list[tuple[int, int]]:
    """Greedy trajectory matching, maximizing matched-frame counts.

    `cost[i][j]` is the number of frames where GT track *i* and predicted
    track *j* both exist and overlap by at least `IOU_MATCH`. Matching is
    greedy over the largest pair counts (deterministic; ties broken by ids).
    """
    all_frames = sorted({f for t in gt + pred for f in t.frames})

    heap: list[tuple[int, int, int]] = []
    for gi, gt_track in enumerate(gt):
        for pi, pred_track in enumerate(pred):
            matched = 0
            for frame in all_frames:
                gt_box = gt_track.bbox_at(frame)
                pred_box = pred_track.bbox_at(frame)
                if (
                    gt_box is not None
                    and pred_box is not None
                    and iou(gt_box, pred_box) >= IOU_MATCH
                ):
                    matched += 1
            if matched > 0:
                heappush(heap, (-matched, gi, pi))

    assigned: list[tuple[int, int]] = []
    used_gt: set[int] = set()
    used_pred: set[int] = set()
    while heap:
        neg, gi, pi = heappop(heap)
        if gi in used_gt or pi in used_pred:
            continue
        assigned.append((gi, pi))
        used_gt.add(gi)
        used_pred.add(pi)

    return assigned


def idf1(gt: list[Tracklet], pred: list[Tracklet]) -> float:
    """Identity F1 across the whole trajectory set.

    Tracks are matched greedily (maximum overlapping frames, then IoU per
    frame). For each matched pair, frames are classified as idTP/idFP/idFN;
    unmatched tracks contribute idFN (ground truth) or idFP (predicted) on
    every frame they occupy, and the global totals are combined into F1.
    """
    assigned = _assignment_matrix(gt, pred)

    idtp = idfp = idfn = 0

    def count_pair(gt_track: Tracklet, pred_track: Tracklet) -> None:
        nonlocal idtp, idfp, idfn
        frames = sorted(gt_track.frames | pred_track.frames)
        for frame in frames:
            gt_box = gt_track.bbox_at(frame)
            pred_box = pred_track.bbox_at(frame)
            if gt_box is None and pred_box is None:
                continue
            if gt_box is None:
                idfp += 1
            elif pred_box is None:
                idfn += 1
            elif iou(gt_box, pred_box) >= IOU_MATCH:
                idtp += 1
            else:
                idfp += 1
                idfn += 1

    matched_gt: set[int] = set()
    matched_pred: set[int] = set()
    for gt_index, pred_index in assigned:
        count_pair(gt[gt_index], pred[pred_index])
        matched_gt.add(gt_index)
        matched_pred.add(pred_index)

    for gt_index, track in enumerate(gt):
        if gt_index not in matched_gt:
            idfn += len(track.observations)
    for pred_index, track in enumerate(pred):
        if pred_index not in matched_pred:
            idfp += len(track.observations)

    return _f1(idtp, idfp, idfn)


def _f1(tp: int, fp: int, fn: int) -> float:
    denom = tp + 0.5 * (fp + fn)
    return tp / denom if denom > 0 else 1.0


def count_accuracy(gt: list[Tracklet], pred: list[Tracklet]) -> tuple[float, float]:
    """Mean absolute/percentage error of per-frame fruit count."""
    frames = sorted({f for t in gt + pred for f in t.frames})
    if not frames:
        return 0.0, 0.0

    gt_counts: dict[int, int] = {}
    pred_counts: dict[int, int] = {}
    for frame in frames:
        gt_counts[frame] = sum(1 for t in gt if t.bbox_at(frame) is not None)
        pred_counts[frame] = sum(1 for t in pred if t.bbox_at(frame) is not None)

    errors = [abs(gt_counts[f] - pred_counts[f]) for f in frames]
    mae = sum(errors) / len(frames)
    mape = (
        sum(e / max(1, gt_counts[f]) for f, e in zip(frames, errors, strict=True))
        / len(frames)
        * 100.0
    )
    return mae, mape


def identity_recovery_rate(recovered: int, total_gaps: int) -> float:
    """Fraction of ground-truth identity gaps that re-id recovered."""
    if total_gaps <= 0:
        return 1.0 if recovered == 0 else 0.0
    return recovered / total_gaps


def _per_frame_match(gt_track: Tracklet, pred: list[Tracklet]) -> dict[int, int | None]:
    """Map every GT observation frame to its best-overlap predicted track.

    Only predicted tracks overlapping the GT box by at least `IOU_MATCH` on
    that frame are candidates; frames without a candidate map to ``None``.
    """
    matches: dict[int, int | None] = {}
    for frame, gt_box in gt_track.observations:
        best_id: int | None = None
        best_iou = IOU_MATCH
        for pred_track in pred:
            pred_box = pred_track.bbox_at(frame)
            if pred_box is None:
                continue
            score = iou(gt_box, pred_box)
            if score >= best_iou:
                best_iou = score
                best_id = pred_track.object_id
        matches[frame] = best_id
    return matches


def id_switch_count(gt: list[Tracklet], pred: list[Tracklet]) -> int:
    """Total predicted-id switches within each ground-truth track.

    A switch occurs when the best-overlap predicted track changes between
    consecutive frames while both assignments exist.
    """
    switches = 0
    for gt_track in gt:
        matches = _per_frame_match(gt_track, pred)
        frames = sorted(matches)
        last: int | None = None
        for frame in frames:
            current = matches[frame]
            if current is not None and last is not None and current != last:
                switches += 1
            last = current
    return switches


def track_fragmentation(gt: list[Tracklet], pred: list[Tracklet]) -> float:
    """Mean number of predicted fragments per ground-truth object.

    A fragment is a maximal run of consecutive frames mapped to the same
    predicted track (gaps map to ``None`` and break runs).
    """
    fragments = []
    for gt_track in gt:
        if not gt_track.observations:
            continue
        matches = _per_frame_match(gt_track, pred)
        runs = 0
        current: int | None = None
        for frame in sorted(matches):
            state = matches[frame]
            if state != current:
                current = state
                if state is not None:
                    runs += 1
        fragments.append(runs)
    if not fragments:
        return 0.0
    return sum(fragments) / len(fragments)


@dataclass(frozen=True, slots=True)
class MetricsReport:
    idf1: float
    id_switches: int
    track_fragmentation: float
    count_mae: float
    count_mape: float
    identity_recovery_rate: float

    def to_dict(self) -> dict:
        return {
            "idf1": round(self.idf1, 4),
            "idSwitches": self.id_switches,
            "trackFragmentation": round(self.track_fragmentation, 4),
            "countMae": round(self.count_mae, 4),
            "countMape": round(self.count_mape, 4),
            "identityRecoveryRate": round(self.identity_recovery_rate, 4),
        }


def evaluate(
    gt: list[Tracklet],
    pred: list[Tracklet],
    recovered: int = 0,
    total_gaps: int = 0,
) -> MetricsReport:
    """Compute the full metric report for a trajectory comparison."""
    mae, mape = count_accuracy(gt, pred)
    return MetricsReport(
        idf1=idf1(gt, pred),
        id_switches=id_switch_count(gt, pred),
        track_fragmentation=track_fragmentation(gt, pred),
        count_mae=mae,
        count_mape=mape,
        identity_recovery_rate=identity_recovery_rate(recovered, total_gaps),
    )
