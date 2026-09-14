"""Pseudo-label clustering for identity self-training.

A dependency-free (numpy-only) DBSCAN over unit-norm embedding vectors is used
to derive pseudo identity labels from tracklet centroids: embeddings extracted
by the current model are clustered, and each clean sub-tracklet inherits the
label of its centroid cluster. Noise points (DBSCAN label ``-1``) are excluded
from anchoring, which keeps pseudo labels reliable as the model improves.

The implementation mirrors the numpy-first philosophy of :mod:`training` —
no scikit-learn dependency for the mock/test milestone.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .dataset import SubTracklet

__all__ = ["PseudoLabelResult", "assign_centroid_pseudo_labels", "dbscan"]


def dbscan(
    vectors: NDArray[np.float32],
    eps: float = 0.3,
    min_samples: int = 3,
) -> NDArray[np.int64]:
    """Density-based clustering over unit-norm vectors.

    Uses cosine distance (``1 - dot``, valid since inputs are unit norm).
    Points with fewer than ``min_samples`` neighbors within ``eps`` are noise
    and receive label ``-1``.

    Args:
        vectors: ``(N, D)`` float array of L2-normalized embeddings.
        eps: Maximum cosine distance for two points to be neighbors.
        min_samples: Minimum neighbors for a point to seed a cluster.

    Returns:
        Integer labels per row; ``-1`` marks noise.
    """
    n = len(vectors)
    if n == 0:
        return np.zeros(0, dtype=np.int64)
    norms = np.linalg.norm(vectors, axis=1)
    sim = vectors @ vectors.T
    sim = np.clip(sim / np.maximum(norms[:, None] * norms[None, :], 1e-9), -1.0, 1.0)
    dist = 1.0 - sim

    labels = np.full(n, -1, dtype=np.int64)
    cluster_id = 0
    for i in range(n):
        if labels[i] != -1:
            continue
        neighbors = np.flatnonzero(dist[i] <= eps)
        if neighbors.size < min_samples:
            continue  # density-reachable noise point, stays -1
        labels[i] = cluster_id
        seed = neighbors[neighbors != i].tolist()
        while seed:
            j = seed.pop()
            if labels[j] != -1:
                continue
            labels[j] = cluster_id
            j_neighbors = np.flatnonzero(dist[j] <= eps)
            if j_neighbors.size >= min_samples:
                seed.extend(j_neighbors[j_neighbors != j].tolist())
        cluster_id += 1
    return labels


@dataclass(frozen=True, slots=True)
class PseudoLabelResult:
    """Pseudo identity labels derived from sub-tracklet centroids.

    Attributes:
        labels: Sub-tracklet index → pseudo-label mapping. Only reliable
            sub-tracklets (clustered, non-noise) appear.
        unlabeled_indices: Sub-tracklet indices excluded (noise / too sparse).
        cluster_count: Number of distinct pseudo identities.
    """

    labels: dict[int, int]
    unlabeled_indices: list[int]
    cluster_count: int


def assign_centroid_pseudo_labels(
    subtracklets: Sequence[SubTracklet],
    eps: float = 0.3,
    min_samples: int = 3,
) -> PseudoLabelResult:
    """Cluster sub-tracklet centroid embeddings into pseudo identities.

    The centroid vector per sub-tracklet is the L2-normalized mean of its
    observation embeddings. Sub-tracklets whose observation vectors are all
    ``None`` are excluded (no embedding available to cluster on).

    Args:
        subtracklets: Clean sub-tracklets from a :class:`TrackletDataset`.
        eps: DBSCAN neighbor threshold (cosine distance).
        min_samples: DBSCAN minimum samples per cluster.

    Returns:
        Pseudo-label assignments keyed by sub-tracklet index.
    """
    indices: list[int] = []
    centroids: list[NDArray[np.float32]] = []
    for index, sub in enumerate(subtracklets):
        vectors = [obs.vector for obs in sub.observations if obs.vector is not None]
        if not vectors:
            continue
        centroid = np.mean(np.stack(vectors), axis=0)
        norm = np.linalg.norm(centroid)
        if not norm:
            continue
        indices.append(index)
        centroids.append((centroid / norm).astype(np.float32))

    if not indices:
        return PseudoLabelResult(labels={}, unlabeled_indices=[], cluster_count=0)

    stacked = np.stack(centroids)
    labels = dbscan(stacked, eps=eps, min_samples=min_samples)

    # Renumber cluster ids to a dense 0..K-1 range (noise stays excluded).
    unique = sorted(int(label) for label in set(labels.tolist()) if label >= 0)
    rename = {old: new for new, old in enumerate(unique)}
    assignments: dict[int, int] = {}
    unlabeled: list[int] = []
    for index, label in zip(indices, labels.tolist(), strict=True):
        if label >= 0:
            assignments[index] = rename[label]
        else:
            unlabeled.append(index)
    return PseudoLabelResult(
        labels=assignments,
        unlabeled_indices=unlabeled,
        cluster_count=len(unique),
    )
