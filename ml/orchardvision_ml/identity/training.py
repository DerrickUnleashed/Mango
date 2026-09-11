"""Self-supervised identity embedding training scaffold.

Implements the pair-generation, filtering, and contrastive-learning pieces that
a real (PyTorch/dataset-backed) training run needs, in a dependency-free numpy
form so the whole loop is executable and testable in the mock-first milestone.

Swap-in boundary: replace :class:`ContrastiveTrainer`'s linear projector with a
small CNN + autograd backend (``torch``) once real appearance embeddings
exist. The :class:`PairSampler` logic — temporal-consistent positives,
spatially-separated negatives, visibility-aware filtering, and hard-negative
mining — is model-agnostic and transfers unchanged.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from statistics import mean

import numpy as np
from numpy.typing import NDArray

from .base import Embedding, cosine_similarity


@dataclass(frozen=True, slots=True)
class PairOptions:
    """Tunables for positive/negative pair construction.

    Attributes:
        max_frames_apart: Temporal window used for positive pairs from the same
            tracklet (temporal consistency).
        min_center_distance: Minimum center-pixel distance between an anchor and
            a negative, enforcing spatial consistency (fruit regions stay
            separated even when appearance is similar).
        include_occluded: Whether occluded/low-confidence observations are kept
            (visibility-aware filtering). Defaults to ``False`` so visibility is
            respected.
        hard_mining_top_k: How many most-anchor-similar negatives to keep per
            anchor (hard-negative mining).
        negative_batch_size: Cap on negatives sampled per anchor.
        temperature: InfoNCE temperature used by the contrastive loss.
    """

    max_frames_apart: int = 15
    min_center_distance: float = 60.0
    include_occluded: bool = False
    hard_mining_top_k: int = 8
    negative_batch_size: int = 32
    temperature: float = 0.1


@dataclass(slots=True)
class TrainingPair:
    anchor: Embedding
    positive: Embedding | None = None
    negatives: list[Embedding] = field(default_factory=list)


class PairSampler:
    """Builds positive/negative training pairs from per-frame embeddings.

    Accepts embeddings produced by any :class:`EmbeddingExtractor`. Embeddings
    are grouped into tracklets (per ``track_id``); a positive is another
    observation of the same tracklet within a temporal window, and negatives
    are observations of *other* tracklets that satisfy a minimum spatial
    separation.
    """

    def __init__(self, options: PairOptions | None = None) -> None:
        self.options = options or PairOptions()

    def build(self, embeddings: Iterable[Embedding]) -> list[TrainingPair]:
        visible = self._filter_visible(list(embeddings))
        tracklets: dict[int, list[Embedding]] = {}
        for emb in visible:
            if emb.track_id is not None:
                tracklets.setdefault(emb.track_id, []).append(emb)
        tracklets = {tid: sorted(embs, key=lambda e: e.frame_id) for tid, embs in tracklets.items()}

        pairs: list[TrainingPair] = []
        for anchor in visible:
            if anchor.track_id is None or anchor.track_id not in tracklets:
                continue
            positive = self._temporal_positive(anchor, tracklets[anchor.track_id])
            negatives = self._hard_negatives(anchor, tracklets, visible)
            pairs.append(TrainingPair(anchor=anchor, positive=positive, negatives=negatives))
        return pairs

    def _filter_visible(self, embeddings: list[Embedding]) -> list[Embedding]:
        if self.options.include_occluded:
            return embeddings
        return [
            emb
            for emb in embeddings
            if not emb.is_occluded and emb.confidence > 0.0 and np.linalg.norm(emb.vector) > 0
        ]

    def _temporal_positive(self, anchor: Embedding, tracklet: list[Embedding]) -> Embedding | None:
        candidates = [
            emb
            for emb in tracklet
            if emb is not anchor
            and abs(emb.frame_id - anchor.frame_id) <= self.options.max_frames_apart
        ]
        if not candidates:
            return None
        # Temporal consistency: prefer the nearest neighbour in time.
        return min(candidates, key=lambda e: abs(e.frame_id - anchor.frame_id))

    def _center_distance(self, a: Embedding, b: Embedding) -> float:
        ab, bb = a.bbox, b.bbox
        if ab is None or bb is None:
            return float("inf")
        ca = (ab[0] + ab[2] / 2.0, ab[1] + ab[3] / 2.0)
        cb = (bb[0] + bb[2] / 2.0, bb[1] + bb[3] / 2.0)
        return float(np.hypot(ca[0] - cb[0], ca[1] - cb[1]))

    def _hard_negatives(
        self,
        anchor: Embedding,
        tracklets: dict[int, list[Embedding]],
        visible: list[Embedding],
    ) -> list[Embedding]:
        pool: list[Embedding] = []
        for tid, embs in tracklets.items():
            if tid == anchor.track_id:
                continue
            if any(
                self._center_distance(anchor, e) >= self.options.min_center_distance for e in embs
            ):
                pool.append(embs[0])
        if not pool:
            pool = [e for e in visible if e is not anchor and e.track_id != anchor.track_id]

        # Hard-negative mining: keep the pool members most similar to the anchor.
        hard = sorted(pool, key=lambda e: cosine_similarity(anchor.vector, e.vector), reverse=True)
        hard = hard[: self.options.hard_mining_top_k]
        if len(hard) <= self.options.negative_batch_size:
            return hard
        rng = np.random.default_rng(seed=hash(anchor.frame_id) & 0xFFFF)
        return [
            hard[i]
            for i in rng.choice(
                len(hard), size=self.options.negative_batch_size, replace=False
            ).tolist()
        ]


@dataclass(frozen=True, slots=True)
class TrainingResult:
    """Outcome of a contrastive training run."""

    projection: NDArray[np.float32]
    loss_history: list[float]
    positive_similarity: float
    negative_similarity: float

    def separation(self) -> float:
        """Mean positive-minus-negative cosine similarity gap after training."""
        return self.positive_similarity - self.negative_similarity


class ContrastiveTrainer:
    """Fits a linear projector with an InfoNCE contrastive objective.

    The projector maps unit-norm input embeddings to a lower-dimensional space;
    the loss pulls same-tracklet (temporal-consistent) projections together and
    pushes spatially-separated, dissimilar-appearing ones apart. A real backend
    would substitute this class with a CNN + autograd; the pair bookkeeping and
    mining already encode the training semantics.
    """

    def __init__(
        self,
        feature_dim: int,
        n_components: int = 32,
        epochs: int = 50,
        learning_rate: float = 0.05,
        weight_decay: float = 1e-4,
        temperature: float = 0.1,
    ) -> None:
        self.feature_dim = feature_dim
        self.n_components = n_components
        self.epochs = epochs
        self.learning_rate = learning_rate
        self.weight_decay = weight_decay
        self.temperature = temperature
        rng = np.random.default_rng(seed=42)
        self._projection = rng.standard_normal((feature_dim, n_components)).astype(
            np.float32
        ) / np.sqrt(feature_dim)

    @property
    def projection(self) -> NDArray[np.float32]:
        return self._projection

    def project(self, vectors: NDArray[np.float32]) -> NDArray[np.float32]:
        out = vectors @ self._projection
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        return out / (norms + 1e-9)

    def train(self, pairs: list[TrainingPair]) -> TrainingResult:
        loss_history: list[float] = []
        for _ in range(self.epochs):
            loss = self._epoch(pairs)
            loss_history.append(loss)

        pos_sim, neg_sim = self._similarities(pairs)
        return TrainingResult(
            projection=self._projection,
            loss_history=loss_history,
            positive_similarity=pos_sim,
            negative_similarity=neg_sim,
        )

    def fit(self, pairs: list[TrainingPair]) -> TrainingResult:
        """Alias of :meth:`train` for the dataset-backed workflow."""
        return self.train(pairs)

    def _epoch(self, pairs: list[TrainingPair]) -> float:
        total_grad = np.zeros_like(self._projection, dtype=np.float64)
        losses: list[float] = []
        seen = 0
        for pair in pairs:
            if pair.positive is None or not pair.negatives:
                continue
            grad, loss = self._pair_gradient(pair)
            total_grad += grad
            losses.append(loss)
            seen += 1
        if seen:
            grad = (total_grad / seen).astype(np.float32)
            self._projection -= self.learning_rate * (grad + self.weight_decay * self._projection)
            return float(mean(losses))
        return 0.0

    def _pair_gradient(self, pair: TrainingPair) -> tuple[NDArray[np.float64], float]:
        """InfoNCE gradient in closed form using ``M = W W^T``.

        With ``s(xa, x) = xa W (x W)^T = xa M x^T``, every similarity term is
        linear in ``M``, so ``dL/dM`` is a sum of outer products and ``dL/dW =
        2 * sym(dL/dM) @ W``. This avoids all normalization headaches and makes
        the surrogate trainer provably correct.
        """
        xa = pair.anchor.vector.astype(np.float64).reshape(-1)
        xp = pair.positive.vector.astype(np.float64).reshape(-1)
        xn = np.stack([n.vector.astype(np.float64) for n in pair.negatives])
        tau = self.temperature

        w = self._projection.astype(np.float64)
        m = w @ w.T

        def sim(x: NDArray[np.float64]) -> float:
            return float(xa @ m @ x)

        sp = sim(xp) / tau
        sn = np.array([sim(x) / tau for x in xn])
        logits = np.concatenate([[sp], sn])
        logsumexp = float(np.logaddexp.reduce(logits))
        loss = -sp + logsumexp

        softmax = np.exp(logits - logsumexp)

        d_m = np.zeros_like(m)
        d_m += (-softmax[0]) * np.outer(xa, xp) / tau
        for i, x in enumerate(xn):
            d_m += softmax[i + 1] * np.outer(xa, x) / tau
        d_m = (d_m + d_m.T) / 2.0

        grad = 2.0 * (d_m @ w)
        return grad, loss

    def _similarities(self, pairs: list[TrainingPair]) -> tuple[float, float]:
        positives: list[float] = []
        negatives: list[float] = []
        for pair in pairs:
            if pair.positive is None:
                continue
            ya = self.project(pair.anchor.vector[None, :])[0]
            yp = self.project(pair.positive.vector[None, :])[0]
            positives.append(float(cosine_similarity(ya, yp)))
            if pair.negatives:
                yns = self.project(np.stack([n.vector for n in pair.negatives]))
                negatives.append(float(mean(cosine_similarity(ya, yn) for yn in yns)))
        if not positives:
            return 0.0, 0.0
        return float(mean(positives)), float(mean(negatives)) if negatives else 0.0
