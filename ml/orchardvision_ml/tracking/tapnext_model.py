"""PyTorch glue over the vendored TAPNext++ wrapper.

The upstream ``tapnextpp.py`` only accepts ``query_points_xy`` on the very
first frame (when ``state`` is ``None``). For multi-object tracking, fruits
enter and leave the frame all the time, so the tracker needs to seed *new*
query points mid-stream. This subclass keeps the vendored upstream files
byte-for-byte and adds one capability: when ``track_frame`` is called with
**both** a recurrent ``state`` and new display pixels, the new points are
appended to the state's query rows (each tagged with the current step, so
the model places its query token on exactly this frame) before the usual
online forward pass.

This module imports torch at the top; it is only imported by
:class:`TAPNextTracker` when a real model is built, never at package import
time.
"""

from __future__ import annotations

import numpy as np
import torch

from .tapnext import TAPNextPP, TAPNextTrackingState, utils


class TAPNextModel(TAPNextPP):
    """TAPNextPP plus mid-stream query seeding."""

    def track_frame(
        self,
        frame_bgr: np.ndarray,
        query_points_xy: np.ndarray | None = None,
        state: TAPNextTrackingState | None = None,
        autocast: bool = True,
    ) -> tuple[np.ndarray, np.ndarray, TAPNextTrackingState]:
        if state is not None and query_points_xy is not None:
            state = self._extend_state(frame_bgr.shape[:2], state, query_points_xy)
            query_points_xy = None
        return super().track_frame(
            frame_bgr,
            query_points_xy=query_points_xy,
            state=state,
            autocast=autocast,
        )

    def _extend_state(
        self,
        hw: tuple[int, int],
        state: TAPNextTrackingState,
        points_xy: np.ndarray,
    ) -> TAPNextTrackingState:
        """Append query rows for newly-seen points at the current step.

        New rows carry ``query_timestep == state.step``, the index of the
        frame about to be processed, so the model's online path (which places
        the point-query token only where ``t - step == 0``) seeds them on
        exactly this frame rather than re-seeding the older queries.
        """
        h, w = hw
        model_pts = utils.display_to_model(points_xy, h, w, self.MODEL_SIZE)
        new_rows = utils.make_query_tensor(model_pts, self.device, query_timestep=state.step)
        state.query_points = torch.cat([state.query_points, new_rows], dim=1)
        return state

    @classmethod
    def from_checkpoint(  # type: ignore[override]
        cls,
        path: str | None = None,
        device: str = "cuda",
        half_precision: bool = False,
        compile_model: bool = False,
        input_resolution: int = TAPNextPP.MODEL_SIZE,
    ) -> TAPNextModel:
        """Load the TAPNext++ checkpoint as a :class:`TAPNextModel`.

        The base implementation already returns ``cls(...)``; this override
        only tightens the return annotation.
        """
        return super().from_checkpoint(
            path=path,
            device=device,
            half_precision=half_precision,
            compile_model=compile_model,
            input_resolution=input_resolution,
        )
