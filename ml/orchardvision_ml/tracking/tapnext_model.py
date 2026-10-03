"""PyTorch glue over the vendored TAPNext++ wrapper.

Upstream ``tapnextpp.py`` returns a plain ``TAPNextPP`` from
``from_checkpoint``. This subclass keeps the vendored upstream files byte
-for-byte and only narrows the return annotation, so callers and tests can
type against :class:`TAPNextModel` directly.

Note on query growth: TAPNext++'s recurrent state keys its SSM caches by
token position, so the live online loop cannot grow its query rows mid-stream
(verified empirically and in the upstream torch colab, which seeds once and
then only steps ``state``). The tracker therefore seeds a fixed query set on
its first frame. Expanding the set mid-stream requires restarting the model
from a checkpoint frame and replaying — :class:`TAPNextTracker` implements
this as an opt-in "rebootstrap" (``rebootstrap_interval``); it re-seeds with
the old plus deferred queries and replays the buffered frames through the
current one.

relies on the vendored ``track_frame`` contract exactly as upstream defines
it. This module pulls in torch transitively through the vendored wrapper, so
it is only imported by :class:`TAPNextTracker` when a real model is built,
never at package import time.
"""

from __future__ import annotations

from .tapnext import TAPNextPP


class TAPNextModel(TAPNextPP):
    """TAPNextPP wrapper with a tightened ``from_checkpoint`` return type."""

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
