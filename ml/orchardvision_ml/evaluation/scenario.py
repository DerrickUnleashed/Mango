"""Ground-truth trajectory extraction for mock fruit scenarios."""

from __future__ import annotations

from orchardvision_ml.detection.mock import MockFruit

from .tracks import Tracklet


def ground_truth_trajectories(fruits: list[MockFruit], num_frames: int) -> list[Tracklet]:
    """Official per-fruit trajectories for a mock orchard scenario.

    Each fruit's world position is sampled every frame (``None`` while it is
    absent or fully occluded), giving the reference tracks evaluation compares
    predicted tracks against.
    """
    traj: list[Tracklet] = []
    for fruit in fruits:
        observations: list[tuple[int, tuple[float, float, float, float]]] = []
        for frame in range(num_frames):
            world = fruit.position_at(frame)
            if world is None:
                continue
            x, y = world
            size = fruit.size
            observations.append(
                (frame, (float(x - size / 2), float(y - size / 2), float(size), float(size)))
            )
        traj.append(Tracklet(object_id=fruits.index(fruit), observations=tuple(observations)))
    return traj
