"""Lightweight Kalman filter for constant-velocity 4-DOF box tracking.

State: ``[u, v, s, r, u', v', s']`` where ``u``/``v`` are the box centre,
``s`` is the box area, and ``r`` is the aspect ratio. This mirrors the
standard ByteTrack/SORT formulation so a real model-mode adapter can swap a
heavier implementation in without changing the tracker interface.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def to_xyah(bbox: tuple[float, float, float, float]) -> NDArray[np.float64]:
    x, y, w, h = bbox
    return np.array([x + w / 2.0, y + h / 2.0, w * h, w / max(h, 1e-6)], dtype=np.float64)


def to_tlwh(state: NDArray[np.float64]) -> tuple[float, float, float, float]:
    u, v, s, r = state[:4]
    w = np.sqrt(s * r)
    h = s / max(w, 1e-6)
    return (u - w / 2.0, v - h / 2.0, w, h)


class KalmanBoxFilter:
    """A Kalman filter tracking a single box with constant velocity."""

    def __init__(self) -> None:
        self._dt = 1.0
        ndim = 7
        self._state = np.zeros(ndim, dtype=np.float64)
        self._cov = np.eye(ndim, dtype=np.float64) * 10.0

        # State transition: constant velocity on (u, v, s); r stays constant
        self._f = np.eye(ndim, dtype=np.float64)
        self._f[0, 4] = self._dt  # u' = u + dt * u_vel
        self._f[1, 5] = self._dt  # v' = v + dt * v_vel
        self._f[2, 6] = self._dt  # s' = s + dt * s_vel

        self._h = np.zeros((4, ndim), dtype=np.float64)
        for i in range(4):
            self._h[i, i] = 1.0

        self._position_std = 1.0
        self._area_std = 1.0
        self._speed_std = 5.0

    def initiate(self, measurement: NDArray[np.float64]) -> None:
        self._state[:4] = measurement
        self._state[4:] = 0.0
        self._cov = np.eye(7, dtype=np.float64) * 100.0

    def predict(self) -> None:
        q = np.eye(7, dtype=np.float64)
        deaccelerate = 0.005
        q[0, 0] = 2.0 * self._position_std**2 * self._dt
        q[1, 1] = 2.0 * self._position_std**2 * self._dt
        q[2, 2] = 2.0 * self._area_std**2 * self._dt
        q[4:, 4:] = self._speed_std**2 * self._dt * 2.0
        q *= deaccelerate

        self._cov = self._f @ self._cov @ self._f.T + q
        self._state = self._f @ self._state

    def update(self, measurement: NDArray[np.float64]) -> None:
        r = np.eye(4, dtype=np.float64) * 1.0
        r[2, 2] = 10.0
        r[3, 3] = 10.0

        y = measurement - self._h @ self._state
        s = self._h @ self._cov @ self._h.T + r
        k = self._cov @ self._h.T @ np.linalg.inv(s)
        self._state = self._state + k @ y
        self._cov = (np.eye(7) - k @ self._h) @ self._cov

    def get_estimate_xyah(self) -> NDArray[np.float64]:
        return self._state[:4].copy()
