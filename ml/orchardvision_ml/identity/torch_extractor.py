"""Pretrained-backbone embedding extractor for fruit appearance.

Crops each detection from the frame, scales it to the backbone's expected
input size, and runs it through the feature trunk of a torchvision model
minus the classification head.  The resulting vector is L2-normalized so
cosine similarity equals dot product, matching the pipeline conventions.

The model loads lazily on first use (weights are downloaded on demand),
keeping import time and disk usage low when only the mock embedder is needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import cv2
import numpy as np
from numpy.typing import NDArray

from orchardvision_ml.detection import FrameDetections

from .base import Embedding, EmbeddingExtractor

if TYPE_CHECKING:
    from torch import nn

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)
DEFAULT_INPUT_SIZE = 224


class TorchEmbeddingExtractor(EmbeddingExtractor):
    """Appearance embedder backed by a pretrained torchvision backbone.

    Args:
        backbone: torchvision model name (``"resnet18"``, ``"resnet34"``, ...).
        embedding_dim: Feature dimension; ``None`` uses the backbone's native
            output dimension.
        input_size: Square crop size fed to the backbone.
        device: Torch device string; ``None`` auto-selects CUDA then CPU.
    """

    def __init__(
        self,
        backbone: str = "resnet18",
        embedding_dim: int | None = None,
        input_size: int = DEFAULT_INPUT_SIZE,
        device: str | None = None,
    ) -> None:
        self.backbone_name = backbone
        self.embedding_dim = embedding_dim
        self.input_size = input_size
        self.device = device
        self._model: nn.Module | None = None
        self._device: str = device or "cpu"

    @property
    def name(self) -> str:
        return f"torch-{self.backbone_name}"

    def extract(
        self, frame: NDArray[np.uint8], frame_detections: FrameDetections
    ) -> list[Embedding]:
        if not frame_detections.detections:
            return []

        import torch

        model, device = self._ensure_model()
        crops = self._extract_crops(frame, frame_detections)
        tensor = torch.from_numpy(np.stack(crops).transpose(0, 3, 1, 2)).to(device)

        with torch.inference_mode():
            features = model(tensor).cpu().numpy()

        result: list[Embedding] = []
        for index, det in enumerate(frame_detections.detections):
            vector = features[index]
            norm = float(np.linalg.norm(vector)) or 1.0
            result.append(
                Embedding(
                    track_id=det.track_id,
                    frame_id=frame_detections.frame_id,
                    vector=(vector / norm).astype(np.float32),
                    confidence=det.confidence,
                    is_occluded=det.confidence < 0.35,
                    bbox=det.bbox,
                )
            )
        return result

    def _ensure_model(self) -> tuple[nn.Module, str]:
        if self._model is not None:
            return self._model, self._device

        import torch
        import torchvision

        self._device = self.device or ("cuda" if torch.cuda.is_available() else "cpu")

        backbone = torchvision.models.get_model(self.backbone_name, weights="IMAGENET1K_V1")

        feature = backbone.fc if hasattr(backbone, "fc") else None
        in_features = feature.in_features if feature is not None else 512
        out_dim = self.embedding_dim or in_features

        model = torch.nn.Sequential(
            *list(backbone.children())[:-1],  # trunk + avgpool, drop the classifier head
            torch.nn.Flatten(1),
            torch.nn.Linear(in_features, out_dim),
            torch.nn.ReLU(inplace=True),
        )
        model.to(self._device).eval()
        self._model = model
        return self._model, self._device

    def _extract_crops(self, frame: NDArray[np.uint8], fd: FrameDetections) -> list[NDArray]:
        h, w = frame.shape[:2]
        crops: list[NDArray] = []
        for det in fd.detections:
            x, y, bw, bh = det.bbox
            x0, y0 = max(0, int(x)), max(0, int(y))
            x1, y1 = min(w, int(x + bw)), min(h, int(y + bh))
            crop = frame[y0:y1, x0:x1]
            if crop.size == 0:
                mid_y, mid_x = h // 2, w // 2
                crop = frame[max(0, mid_y - 32) : mid_y + 32, max(0, mid_x - 32) : mid_x + 32]
            resized = cv2.resize(
                crop, (self.input_size, self.input_size), interpolation=cv2.INTER_LINEAR
            )
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            # Normalized into a new binding rather than reassigning rgb:
            # reassigning made mypy infer the numpy expression's type as
            # complex128, which it is not.
            normalized = (rgb - np.asarray(IMAGENET_MEAN, np.float32)) / np.asarray(
                IMAGENET_STD, np.float32
            )
            crops.append(normalized)
        return crops
