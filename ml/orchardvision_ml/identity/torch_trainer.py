"""PyTorch contrastive trainer for identity embeddings.

Completes the swap-in boundary documented in :mod:`training`: the numpy
linear-projector surrogate (:class:`training.ContrastiveTrainer`) is replaced
by a real CNN backbone + MLP projection head trained with an InfoNCE objective
on the crop pairs built by :class:`dataset.TrackletDataset`.

The pair bookkeeping (temporal positives, spatially-separated negatives,
visibility filtering, hard-negative mining) is unchanged — it happens at the
observation level before cropping. This module only maps observations to crops
and crops to embeddings.

torch/torchvision are imported lazily so mock-only environments never pay the
import or model-weight download cost.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from .dataset import CropPair, TrackObservation, crop_observation

if TYPE_CHECKING:
    import torch
    from torch import nn

try:
    import torch
except ImportError:  # pragma: no cover - mock environments may lack torch
    torch = None  # type: ignore[assignment]


@dataclass(frozen=True, slots=True)
class TorchTrainerConfig:
    """Hyper-parameters for the contrastive training run.

    Attributes:
        backbone: torchvision model name used as the CNN trunk.
        embed_dim: Dimension of the learned L2-normalized embedding.
        hidden_dim: Width of the projection MLP hidden layer.
        input_size: Square crop size fed to the backbone.
        temperature: InfoNCE temperature; lower values sharpen logits.
        learning_rate: AdamW learning rate.
        weight_decay: AdamW weight decay.
        epochs: Number of full passes over the pair list.
        batch_size: Number of (anchor, positive, negatives) pairs per step.
        device: Torch device; ``None`` auto-selects CUDA then CPU.
        seed: Random seed for reproducible initialization/data ordering.
    """

    backbone: str = "resnet18"
    embed_dim: int = 128
    hidden_dim: int = 512
    input_size: int = 224
    temperature: float = 0.1
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    epochs: int = 10
    batch_size: int = 4
    device: str | None = None
    seed: int = 42


@dataclass(frozen=True, slots=True)
class TorchTrainingResult:
    """Outcome of a contrastive training run."""

    loss_history: list[float]
    positive_similarity: float
    negative_similarity: float

    def separation(self) -> float:
        """Mean positive-minus-negative cosine similarity gap after training."""
        return self.positive_similarity - self.negative_similarity


FrameProvider = Callable[[str, int], NDArray[np.uint8]]


class IdentityEmbeddingNet:
    """CNN trunk + projection head producing L2-normalized embeddings.

    Attributes:
        backbone_name: torchvision backbone name used to build the trunk.
        embed_dim: Output embedding dimension.
        hidden_dim: Width of the projection MLP hidden layer.
        input_size: Square crop size fed to the backbone.
        device: Resolved torch device string.
    """

    def __init__(
        self,
        backbone_name: str = "resnet18",
        embed_dim: int = 128,
        hidden_dim: int = 512,
        input_size: int = 224,
        device: str | None = None,
    ) -> None:
        if torch is None:  # pragma: no cover
            raise ImportError("torch is required for the contrastive training backend")
        self.backbone_name = backbone_name
        self.embed_dim = embed_dim
        self.hidden_dim = hidden_dim
        self.input_size = input_size
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._model: nn.Module | None = None

    @property
    def model(self) -> nn.Module:
        if self._model is None:
            self._model = self._build()
        return self._model

    def _build(self) -> nn.Module:
        import torchvision

        backbone = torchvision.models.get_model(
            self.backbone_name, weights="IMAGENET1K_V1"
        )
        feature = backbone.fc if hasattr(backbone, "fc") else None
        in_features = feature.in_features if feature is not None else 512

        trunk = torch.nn.Sequential(
            *list(backbone.children())[:-1],  # conv trunk + avgpool, drop classifier
            torch.nn.Flatten(1),
        )
        projector = torch.nn.Sequential(
            torch.nn.Linear(in_features, self.hidden_dim),
            torch.nn.BatchNorm1d(self.hidden_dim),
            torch.nn.ReLU(inplace=True),
            torch.nn.Linear(self.hidden_dim, self.embed_dim),
            torch.nn.BatchNorm1d(self.embed_dim),
        )
        model = torch.nn.Sequential(trunk, projector)
        model.to(self.device)
        return model

    def __call__(self, tensors: torch.Tensor) -> torch.Tensor:
        features = self.model(tensors)
        return torch.nn.functional.normalize(features, dim=1)

    def state_dict(self) -> dict[str, torch.Tensor]:
        return self.model.state_dict()

    def load_state_dict(self, state: dict[str, torch.Tensor]) -> None:
        self.model.load_state_dict(state)

    def to_checkpoint(self, path: str | Path) -> None:
        torch.save(
            {
                "backbone_name": self.backbone_name,
                "embed_dim": self.embed_dim,
                "hidden_dim": self.hidden_dim,
                "input_size": self.input_size,
                "state_dict": self.state_dict(),
            },
            str(path),
        )


def collate_pairs(
    pairs: Sequence[CropPair],
    frames: FrameProvider,
    input_size: int,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """Batch crop pairs into anchor/positive/negative tensors.

    Returns ``(anchors, positives, negatives, negative_mask)`` where
    ``anchors``/``positives`` are ``(B, 3, H, W)``, ``negatives`` is
    ``(B, max_negatives, 3, H, W)``, and ``negative_mask`` is a ``(B,
    max_negatives)`` float tensor (1 for real negatives, 0 for padding).
    """
    max_negatives = max((len(pair.negatives) for pair in pairs), default=0)
    anchor_crops: list[NDArray] = []
    positive_crops: list[NDArray] = []
    negative_crops: list[list[NDArray]] = []
    negative_mask: list[list[float]] = []
    for pair in pairs:
        anchor_crop = crop_observation(
            frames(pair.anchor.source_id, pair.anchor.frame_id),
            pair.anchor,
            input_size,
        )
        if pair.positive is not None:
            positive_crop = crop_observation(
                frames(pair.positive.source_id, pair.positive.frame_id),
                pair.positive,
                input_size,
            )
        else:
            positive_crop = anchor_crop
        anchor_crops.append(anchor_crop)
        positive_crops.append(positive_crop)

        negatives: list[NDArray] = []
        for negative in pair.negatives[:max_negatives]:
            negatives.append(
                crop_observation(
                    frames(negative.source_id, negative.frame_id),
                    negative,
                    input_size,
                )
            )
        while len(negatives) < max_negatives:
            negatives.append(np.zeros_like(anchor_crop))
        negative_crops.append(negatives)
        negative_mask.append(
            [1.0] * len(pair.negatives) + [0.0] * (max_negatives - len(pair.negatives))
        )

    return (
        torch.as_tensor(np.stack(anchor_crops)).float(),
        torch.as_tensor(np.stack(positive_crops)).float(),
        torch.as_tensor(np.stack(negative_crops)).float(),
        torch.as_tensor(np.asarray(negative_mask)).float(),
    )


class TorchContrastiveTrainer:
    """Trains an :class:`IdentityEmbeddingNet` with an InfoNCE objective.

    Consumes the observation pairs produced by :class:`dataset.TrackletDataset`
    and crops each observation through ``frames`` (a ``source_id, frame_id`` →
    BGR frame callable). Positives are pulled together while negatives —
    hard-mined at the observation level upstream — are pushed apart.
    """

    def __init__(self, config: TorchTrainerConfig | None = None) -> None:
        if torch is None:  # pragma: no cover
            raise ImportError("torch is required for the contrastive training backend")
        self.config = config or TorchTrainerConfig()
        self.net = IdentityEmbeddingNet(
            backbone_name=self.config.backbone,
            embed_dim=self.config.embed_dim,
            hidden_dim=self.config.hidden_dim,
            input_size=self.config.input_size,
            device=self.config.device,
        )

    @property
    def name(self) -> str:
        return f"torch-{self.config.backbone}-{self.config.embed_dim}d"

    def train(
        self,
        pairs: Sequence[CropPair],
        frames: FrameProvider,
    ) -> TorchTrainingResult:
        torch.manual_seed(self.config.seed)
        model = self.net.model
        device = self.net.device
        model.train()
        optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
        )
        completions = [pair for pair in pairs if pair.positive is not None and pair.negatives]
        loss_history: list[float] = []
        for _ in range(self.config.epochs):
            if completions:
                completions = [completions[i] for i in torch.randperm(len(completions)).tolist()]
            epoch_losses: list[float] = []
            for start in range(0, len(completions), self.config.batch_size):
                chunk = completions[start : start + self.config.batch_size]
                if len(chunk) == 1:
                    chunk = chunk + chunk  # BatchNorm needs >1 sample in train mode
                anchors, positives, negatives, mask = collate_pairs(
                    chunk, frames, self.config.input_size
                )
                loss = self._loss_step(
                    optimizer,
                    anchors.to(device),
                    positives.to(device),
                    negatives.to(device),
                    mask.to(device),
                )
                epoch_losses.append(float(loss))
            loss_history.append(float(np.mean(epoch_losses)) if epoch_losses else 0.0)
        pos_sim, neg_sim = self._similarities(completions, frames)
        return TorchTrainingResult(
            loss_history=loss_history,
            positive_similarity=pos_sim,
            negative_similarity=neg_sim,
        )

    def save(self, path: str | Path) -> str:
        self.net.to_checkpoint(path)
        return str(path)

    def _loss_step(
        self,
        optimizer: torch.optim.Optimizer,
        anchors: torch.Tensor,
        positives: torch.Tensor,
        negatives: torch.Tensor,
        negative_mask: torch.Tensor,
    ) -> torch.Tensor:
        optimizer.zero_grad(set_to_none=True)
        emb_a = self.net(anchors)
        emb_p = self.net(positives)
        batch_size, max_negatives = negatives.shape[:2]
        emb_n = self.net(
            negatives.reshape(batch_size * max_negatives, *negatives.shape[2:])
        ).reshape(batch_size, max_negatives, -1)

        tau = self.config.temperature
        sim_pos = (emb_a * emb_p).sum(dim=1) / tau  # (B,)
        sim_neg = torch.einsum("bd,bnd->bn", emb_a, emb_n) / tau  # (B, N)
        logits = torch.cat([sim_pos.unsqueeze(1), sim_neg], dim=1)
        full_mask = torch.cat(
            [torch.ones(batch_size, 1, device=logits.device), negative_mask], dim=1
        )
        logits = torch.where(
            full_mask.bool(),
            logits,
            torch.tensor(float("-inf"), dtype=logits.dtype, device=logits.device),
        )
        labels = torch.zeros(batch_size, dtype=torch.long, device=logits.device)
        loss = torch.nn.functional.cross_entropy(logits, labels)
        loss.backward()
        optimizer.step()
        return loss.detach()

    def _similarities(
        self, completions: list[CropPair], frames: FrameProvider
    ) -> tuple[float, float]:
        if not completions:
            return 0.0, 0.0
        self.net.model.eval()
        positives: list[float] = []
        negatives: list[float] = []
        with torch.inference_mode():
            for pair in completions:
                if pair.positive is None or not pair.negatives:
                    continue
                a = self._embed(frames, pair.anchor)
                p = self._embed(frames, pair.positive)
                positives.append(float(torch.nn.functional.cosine_similarity(a, p, dim=0).item()))
                neg_sims = [
                    float(
                        torch.nn.functional.cosine_similarity(
                            a, self._embed(frames, negative), dim=0
                        ).item()
                    )
                    for negative in pair.negatives
                ]
                negatives.append(float(np.mean(neg_sims)))
        self.net.model.train()
        return (
            float(np.mean(positives)) if positives else 0.0,
            float(np.mean(negatives)) if negatives else 0.0,
        )

    def _embed(
        self, frames: FrameProvider, observation: TrackObservation
    ) -> torch.Tensor:
        crop = crop_observation(
            frames(observation.source_id, observation.frame_id),
            observation,
            self.config.input_size,
        )
        tensor = torch.as_tensor(crop[None, ...]).float().to(self.net.device)
        return self.net(tensor).squeeze(0)
