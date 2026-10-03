"""TAPNext++ (Google DeepMind) PyTorch inference code, vendored.

Copied from the upstream repository at commit ``730cda1c``
(https://github.com/google-deepmind/tapnet, Apache-2.0). The only change to
the upstream source is rewriting the internal package imports to relative
imports so the code runs inside ``orchardvision_ml`` without the ``tapnet``
package installed.

Importing this subpackage requires torch, torchvision and einops. Always
import it lazily (inside functions), and only from the tracker adapter, so a
plain ``orchardvision_ml`` install without the ``tapnext`` extra stays torch
free.
"""

from .tapnext_torch import TAPNext, TAPNextTrackingState
from .tapnextpp import TAPNextPP

__all__ = ["TAPNext", "TAPNextPP", "TAPNextTrackingState"]