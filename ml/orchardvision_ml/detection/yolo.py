"""YOLO detector adapter.

Wraps a ``ultralytics`` YOLO model (v8/v11) behind the shared
:class:`~orchardvision_ml.detection.base.Detector` interface. ``ultralytics``
is an optional dependency: importing the module never imports it, and
instantiating :class:`YOLODetector` with a pre-built model object (for tests or
in-process reuse) skips the lookup entirely.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from .base import Detection, Detector, FrameDetections
from .nms import filter_by_class, nms


class YOLODetector(Detector):
    """Detector that runs an ultralytics YOLO model and post-processes with NMS.

    Args:
        model_path_or_model: Path to a ``.pt`` weights file, or an already
            constructed ultralytics ``YOLO`` instance (for testability and to
            avoid re-instantiating a loaded model).
        confidence_threshold: Minimum confidence to keep a box.
        iou_threshold: NMS suppression threshold.
        class_filter: Restrict results to these class labels (e.g. ``{"mango"}``).
            ``None`` keeps every class.
    """

    def __init__(
        self,
        model_path_or_model: str | Any,
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        class_filter: set[str] | None = None,
    ) -> None:
        self._model = self._build(model_path_or_model)
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.class_filter = class_filter

    @staticmethod
    def _build(model_path_or_model: str | Any) -> Any:
        if not isinstance(model_path_or_model, str):
            return model_path_or_model
        try:
            from ultralytics import YOLO
        except ModuleNotFoundError as exc:  # pragma: no cover - import error path
            raise ImportError(
                "YOLODetector requires the optional 'ultralytics' dependency. "
                "Install it (uv add --project ml ultralytics) or pass a pre-built "
                "model object instead of a path."
            ) from exc
        return YOLO(model_path_or_model)

    @property
    def name(self) -> str:
        return "yolo"

    def detect(self, frame: NDArray[np.uint8], frame_id: int) -> FrameDetections:
        result = self._model.predict(frame, verbose=False)
        result = result[0] if isinstance(result, (list, tuple)) else result

        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return FrameDetections(frame_id=frame_id)

        xywh = boxes.xywh.cpu().numpy() if hasattr(boxes.xywh, "cpu") else np.asarray(boxes.xywh)
        scores = boxes.conf.cpu().numpy() if hasattr(boxes.conf, "cpu") else np.asarray(boxes.conf)
        labels = boxes.cls.cpu().numpy() if hasattr(boxes.cls, "cpu") else np.asarray(boxes.cls)
        names: dict[int, str] = getattr(result.names, "copy", lambda: result.names)()

        candidates: list[tuple[float, float, float, float]] = []
        candidate_scores: list[float] = []
        candidate_labels: list[str] = []

        for bbox, conf, cls_id in zip(xywh.tolist(), scores.tolist(), labels.tolist(), strict=True):
            if conf < self.confidence_threshold:
                continue
            label = names.get(int(cls_id), f"class_{int(cls_id)}")
            x, y, w, h = (float(v) for v in bbox)
            candidates.append((x, y, w, h))
            candidate_scores.append(float(conf))
            candidate_labels.append(label)

        keep_mask = filter_by_class(candidate_labels, self.class_filter)
        filtered_idx = [i for i, keep in enumerate(keep_mask) if keep]
        boxes_filtered = [candidates[i] for i in filtered_idx]
        scores_filtered = [candidate_scores[i] for i in filtered_idx]
        labels_filtered = [candidate_labels[i] for i in filtered_idx]

        keep = nms(boxes_filtered, scores_filtered, iou_threshold=self.iou_threshold)

        detections = [
            Detection(
                bbox=boxes_filtered[i],
                confidence=scores_filtered[i],
                class_label=labels_filtered[i],
            )
            for i in keep
        ]
        detections.sort(key=lambda d: d.confidence, reverse=True)
        return FrameDetections(frame_id=frame_id, detections=detections)
