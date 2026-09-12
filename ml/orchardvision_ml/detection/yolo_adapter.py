"""YOLOv8 detector adapter for mango detection.

Wraps ``ultralytics.YOLO`` behind the :class:`Detector` interface so the rest
of the pipeline stays model-agnostic.  Supports both a pretrained checkpoint
(e.g. ``yolov8n.pt``) and a fine-tuned orchard model.

``ultralytics`` is an optional dependency: importing this module never imports
it, and passing a pre-built model object (for tests or in-process reuse) skips
the lookup entirely.

Coordinates are converted from YOLO's ``xyxy`` pixel format to the
``[x, y, width, height]`` convention used by :class:`Detection`.
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from .base import Detection, Detector, FrameDetections


class YoloDetector(Detector):
    """YOLOv8-based fruit detector.

    Args:
        model_path_or_model: Path to a ``.pt`` weights file (pretrained or
            fine-tuned), or an already constructed ultralytics ``YOLO``
            instance.
        conf_threshold: Minimum confidence to keep a detection.
        iou_threshold: NMS IoU threshold passed to the model.
        class_names: Mapping from class index to label. Defaults to
            ``{0: "mango"}``.
        device: Inference device (``"cpu"``, ``"cuda"``, etc.).  ``None`` lets
            ultralytics pick automatically.
        sliced: When >= 2, run inference per tile over an ``N x N`` grid and
            merge the boxes (small/hidden fruit in wide canopy frames are
            missed at whole-image scale).  ``0`` disables slicing.
        slice_overlap: Fraction of each tile dimension used as overlap between
            adjacent tiles (applies when ``sliced >= 2``).
    """

    def __init__(
        self,
        model_path_or_model: str | Any,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        class_names: dict[int, str] | None = None,
        device: str | None = None,
        sliced: int = 0,
        slice_overlap: float = 0.2,
    ) -> None:
        self._model = self._build(model_path_or_model)
        self._conf = conf_threshold
        self._iou = iou_threshold
        self._class_names = class_names or {0: "mango"}
        self._device = device
        self._sliced = sliced
        self._slice_overlap = slice_overlap

    @staticmethod
    def _build(model_path_or_model: str | Any) -> Any:
        if not isinstance(model_path_or_model, (str, bytes)):
            return model_path_or_model
        try:
            from ultralytics import YOLO
        except ModuleNotFoundError as exc:  # pragma: no cover - import error path
            raise ImportError(
                "YoloDetector requires the optional 'ultralytics' dependency. "
                "Install it (uv add --project ml ultralytics) or pass a pre-built "
                "model object instead of a path."
            ) from exc
        return YOLO(str(model_path_or_model))

    @property
    def name(self) -> str:
        return getattr(self._model, "model_name", "yolo-unknown")

    def detect(self, frame: NDArray[np.uint8], frame_id: int) -> FrameDetections:
        """Run YOLOv8 inference on a single BGR frame.

        Args:
            frame: ``(H, W, 3)`` uint8 BGR image from OpenCV.
            frame_id: Zero-based frame index (unused by YOLO but kept for the
                interface contract).

        Returns:
            Detections filtered by confidence and converted to the pipeline's
            coordinate convention.
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        if self._sliced >= 2:
            return self._detect_sliced(frame, frame_id)

        results = self._model.predict(
            source=rgb,
            conf=self._conf,
            iou=self._iou,
            device=self._device,
            verbose=False,
        )

        detections: list[Detection] = []

        if results and results[0].boxes is not None:
            boxes = results[0].boxes
            xyxy = boxes.xyxy.cpu().numpy()
            confs = boxes.conf.cpu().numpy()
            clss = boxes.cls.cpu().numpy().astype(int)

            for bbox, conf, cls_idx in zip(xyxy, confs, clss, strict=True):
                if conf < self._conf:
                    continue
                x1, y1, x2, y2 = bbox
                w = x2 - x1
                h = y2 - y1
                label = self._class_names.get(int(cls_idx), "mango")
                detections.append(
                    Detection(
                        bbox=(float(x1), float(y1), float(w), float(h)),
                        confidence=float(conf),
                        class_label=label,
                    )
                )

        detections.sort(key=lambda d: d.confidence, reverse=True)
        return FrameDetections(frame_id=frame_id, detections=detections)

    def _detect_sliced(self, frame: NDArray[np.uint8], frame_id: int) -> FrameDetections:
        """Run detection on overlapping tiles and merge into frame coordinates.

        Wide canopy frames bury small fruit below the effective resolution of a
        single whole-image pass; running the model per tile recovers them.  The
        per-tile boxes are shifted back to frame coordinates and merged with
        the shared non-maximum suppression used by the pipeline.
        """
        from .nms import nms

        h, w = frame.shape[:2]
        grid = self._sliced
        tile_h, tile_w = h // grid, w // grid
        pad_h, pad_w = int(tile_h * self._slice_overlap), int(tile_w * self._slice_overlap)

        raw: list[tuple[float, float, float, float, float, int]] = []
        for gy in range(grid):
            for gx in range(grid):
                x0 = max(0, gx * tile_w - pad_w)
                y0 = max(0, gy * tile_h - pad_h)
                x1 = min(w, (gx + 1) * tile_w + pad_w)
                y1 = min(h, (gy + 1) * tile_h + pad_h)
                tile = frame[y0:y1, x0:x1]
                if tile.shape[0] < 16 or tile.shape[1] < 16:
                    continue
                results = self._model.predict(
                    source=cv2.cvtColor(tile, cv2.COLOR_BGR2RGB),
                    conf=self._conf,
                    iou=self._iou,
                    device=self._device,
                    verbose=False,
                )
                boxes = results[0].boxes
                if boxes is None:
                    continue
                xyxy = boxes.xyxy.cpu().numpy()
                if xyxy.shape[0] == 0:
                    continue
                for bbox, conf, cls_idx in zip(
                    xyxy,
                    boxes.conf.cpu().numpy(),
                    boxes.cls.cpu().numpy().astype(int),
                    strict=True,
                ):
                    if conf < self._conf:
                        continue
                    xl, yl, xr, yr = bbox
                    bw, bh = xr - xl, yr - yl
                    if bw < 2 or bh < 2:
                        continue
                    raw.append(
                        (
                            float(xl + x0),
                            float(yl + y0),
                            float(bw),
                            float(bh),
                            float(conf),
                            int(cls_idx),
                        )
                    )

        if not raw:
            return FrameDetections(frame_id=frame_id, detections=[])

        kept = nms(
            [(b[0], b[1], b[2], b[3]) for b in raw],
            [b[4] for b in raw],
            self._iou,
        )
        merged: list[Detection] = []
        for index in kept:
            x, y, bw, bh, conf, cls_idx = raw[index]
            label = self._class_names.get(cls_idx, "mango")
            merged.append(
                Detection(
                    bbox=(x, y, bw, bh),
                    confidence=conf,
                    class_label=label,
                )
            )
        merged.sort(key=lambda d: d.confidence, reverse=True)
        return FrameDetections(frame_id=frame_id, detections=merged)
