"""Trained identity embedder (self-supervised checkpoint swap-in).

Completes the TODO boundary named by :mod:`training`: production inference
uses the network trained by :mod:`pseudo_trainer` (``SelfSupervisedTrainer``)
instead of the frozen pretrained trunk. Loads the checkpoint written by
``IdentityEmbeddingNet.to_checkpoint`` and forwards crops through the projected
L2-normalized head — the same feature space the pipeline's memory banks index.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from orchardvision_ml.detection import FrameDetections

from .base import Embedding, EmbeddingExtractor
from .dataset import TrackObservation, crop_observation
from .torch_trainer import IdentityEmbeddingNet

__all__ = ["Embedder"]


class Embedder(EmbeddingExtractor):
    """Appearance embedder backed by a self-supervised identity checkpoint.

    Args:
        model_path: Checkpoint produced by ``torch_trainer`` / ``pseudo_trainer``
            (``backbone_name``, ``embed_dim``, ``hidden_dim``, ``input_size``,
            ``state_dict``).
        device: Torch device string; ``None`` auto-selects CUDA then CPU.
    """

    def __init__(
        self,
        model_path: str | Path,
        device: str | None = None,
    ) -> None:
        import torch

        checkpoint = torch.load(str(model_path), map_location="cpu", weights_only=False)
        self.backbone_name = checkpoint["backbone_name"]
        self.embed_dim = checkpoint["embed_dim"]
        self.hidden_dim = checkpoint["hidden_dim"]
        self.input_size = checkpoint["input_size"]
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.net = IdentityEmbeddingNet(
            backbone_name=self.backbone_name,
            embed_dim=self.embed_dim,
            hidden_dim=self.hidden_dim,
            input_size=self.input_size,
            device=self.device,
        )
        self.net.load_state_dict(checkpoint["state_dict"])
        self.net.model.eval()

    @property
    def name(self) -> str:
        return f"trained-{self.backbone_name}-{self.embed_dim}d"

    def extract(
        self, frame: NDArray[np.uint8], frame_detections: FrameDetections
    ) -> list[Embedding]:
        if not frame_detections.detections:
            return []

        import torch

        crops = [
            crop_observation(
                frame,
                TrackObservation(
                    track_id=0,
                    frame_id=frame_detections.frame_id,
                    bbox=det.bbox,
                ),
                self.input_size,
            )
            for det in frame_detections.detections
        ]
        tensor = torch.from_numpy(np.stack(crops)).float().to(self.device)

        with torch.inference_mode():
            vectors = self.net(tensor).cpu().numpy()

        result: list[Embedding] = []
        for index, det in enumerate(frame_detections.detections):
            vector = vectors[index]
            result.append(
                Embedding(
                    track_id=det.track_id,
                    frame_id=frame_detections.frame_id,
                    vector=vector.astype(np.float32),
                    confidence=det.confidence,
                    is_occluded=det.confidence < 0.35,
                    bbox=det.bbox,
                )
            )
        return result
