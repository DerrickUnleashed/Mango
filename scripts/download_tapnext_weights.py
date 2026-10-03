"""Download the TAPNext++ model weights for the ``tapnext++`` tracker backend.

TAPNext++ (Google DeepMind, Tracking-Any-Point with next-generation point
vision transformers, CVPR 2026) publishes its PyTorch checkpoints on Google
Cloud Storage under the Apache-2.0 license:

* ``tapnextpp_ckpt.pt``   — 256x256 model (default, ~170 MB)
* ``tapnextpp_512.ckpt``  — 512x512 model (higher detail, ~170 MB)

The checkpoint is the raw ``nn.Module`` state dict consumed by
``TAPNextTracker`` (pass it as ``checkpoint_path``) or directly by
``TAPNextModel.from_checkpoint``.

Usage::

    python scripts/download_tapnext_weights.py [--resolution 256] [--output models/tapnextpp_ckpt.pt]

Requires the ``tapnext`` extra (``uv sync --project ml --extra tapnext``);
falls back to urllib if ``requests`` is missing.
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

URLS = {
    256: "https://storage.googleapis.com/dm-tapnet/tapnextpp/tapnextpp_ckpt.pt",
    512: "https://storage.googleapis.com/gresearch/tapnextpp/tapnextpp_512.ckpt",
}
DEFAULT_OUTPUTS = {
    256: "models/tapnextpp_ckpt.pt",
    512: "models/tapnextpp_512.ckpt",
}
CHUNK_BYTES = 1024 * 1024


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    total = 0
    try:
        import requests  # type: ignore[import-not-found]

        with requests.get(url, stream=True, timeout=60) as resp:
            resp.raise_for_status()
            with tmp.open("wb") as handle:
                for chunk in resp.iter_content(chunk_size=CHUNK_BYTES):
                    if not chunk:
                        continue
                    handle.write(chunk)
                    total += len(chunk)
                    print(
                        f"\rDownloaded {total / (1 << 20):.1f} MB", end="", flush=True
                    )
    except ImportError:
        with urllib.request.urlopen(url, timeout=60) as resp, tmp.open("wb") as handle:
            while True:
                chunk = resp.read(CHUNK_BYTES)
                if not chunk:
                    break
                handle.write(chunk)
                total += len(chunk)
                print(f"\rDownloaded {total / (1 << 20):.1f} MB", end="", flush=True)
    print()
    tmp.replace(dest)
    print(f"Saved to {dest} ({total / (1 << 20):.1f} MB).")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--resolution",
        type=int,
        choices=sorted(URLS),
        default=256,
        help="Model input resolution (must match the checkpoint). Default: 256.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Destination path. Defaults to models/tapnextpp_ckpt.pt (256) or "
        "models/tapnextpp_512.ckpt (512).",
    )
    args = parser.parse_args(argv)

    output = args.output or Path(DEFAULT_OUTPUTS[args.resolution])
    _download(URLS[args.resolution], output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
