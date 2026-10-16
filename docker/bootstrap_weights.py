#!/usr/bin/env python
"""Fetch model weights on container start, rather than baking them into the image.

The weight tree is ~3.7G, dominated by the TAPNext++ checkpoint at 2.4G. Baking
that into a Docker image inflates the build context, the layer cache and the
image itself, and most managed hosts cap image size well below what that
needs. Fetching on first boot keeps the image small and lets each weight come
from wherever it actually lives.

Three sources, all optional and controlled by env vars:

  * YOLO detector -- ``YOLO_WEIGHTS_URL``, typically a Supabase Storage object.
  * TAPNext++ tracker -- ``TAPNEXT_CHECKPOINT_URL``, a public Google Cloud
    Storage object, so no credential is needed.
  * Identity embedder -- ``EMBEDDER_URL``, typically a Supabase Storage object.

Nothing is fetched from the repo tree: .dockerignore excludes ``models/`` and
``*.pt``, so no weight is ever present in the image. ``YOLO_WEIGHTS_SOURCE=repo``
is kept for local runs that do have the tree mounted.

Every step is idempotent: a weight already present at the target path is left
alone, so the second and later boots are no-ops. Set the matching
``BOOTSTRAP_*`` flag to ``false`` to skip a weight entirely, which is what the
mock-inference and test paths do.
"""

from __future__ import annotations

import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT_DIR = Path(os.environ.get("APP_ROOT_DIR", "/orchardvision"))
WEIGHTS_DIR = Path(os.environ.get("WEIGHTS_DIR", "/data/models"))

TAPNEXT_URL = os.environ.get(
    "TAPNEXT_CHECKPOINT_URL",
    "https://storage.googleapis.com/dm-tapnet/tapnextpp/tapnextpp_ckpt.pt",
)
REPO_YOLO_WEIGHTS = ROOT_DIR / "models" / "mango_yolov8n-4" / "weights" / "best.pt"

_DOWNLOAD_TIMEOUT = 60
_CHUNK = 1024 * 1024


def _flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _log(message: str) -> None:
    print(f"bootstrap_weights: {message}", flush=True)


def _download(url: str, dest: Path) -> None:
    """Stream ``url`` to ``dest`` via a temp file, so a partial download never
    leaves a corrupt weight that the next boot would treat as complete."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    _log(f"downloading {url} -> {dest}")
    try:
        with urllib.request.urlopen(url, timeout=_DOWNLOAD_TIMEOUT) as response:
            with tmp.open("wb") as handle:
                shutil.copyfileobj(response, handle, _CHUNK)
        tmp.replace(dest)
    except urllib.error.URLError as exc:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"failed to download {url}: {exc}") from exc


def _fetch_tapnext() -> None:
    if not _flag("BOOTSTRAP_TAPNEXT", True):
        _log("TAPNext bootstrap disabled (BOOTSTRAP_TAPNEXT=false)")
        return
    dest = WEIGHTS_DIR / "tapnextpp_ckpt.pt"
    if dest.exists() and dest.stat().st_size > 0:
        _log(f"TAPNext checkpoint already present ({dest.stat().st_size // (1024 * 1024)} MiB)")
        return
    _download(TAPNEXT_URL, dest)


def _fetch_yolo() -> None:
    if not _flag("BOOTSTRAP_YOLO", True):
        _log("YOLO bootstrap disabled (BOOTSTRAP_YOLO=false)")
        return
    dest = WEIGHTS_DIR / "mango_yolov8n-4" / "weights" / "best.pt"
    if dest.exists() and dest.stat().st_size > 0:
        _log(f"YOLO weights already present ({dest.stat().st_size} bytes)")
        return

    url = os.environ.get("YOLO_WEIGHTS_URL")
    if url:
        _download(url, dest)
        return

    source = os.environ.get("YOLO_WEIGHTS_SOURCE", "repo")
    if source.startswith(("http://", "https://")):
        _download(source, dest)
        return

    if not REPO_YOLO_WEIGHTS.exists():
        _log("no YOLO_WEIGHTS_URL set and no repo weights present; skipping")
        return

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO_YOLO_WEIGHTS, dest)
    _log(f"copied YOLO weights from repo ({dest.stat().st_size} bytes)")


def _fetch_embedder() -> None:
    if not _flag("BOOTSTRAP_EMBEDDER", False):
        return
    url = os.environ.get("EMBEDDER_URL")
    if not url:
        _log("EMBEDDER_URL unset; skipping identity embedder")
        return
    dest = WEIGHTS_DIR / "identity" / "embedder.pt"
    if dest.exists() and dest.stat().st_size > 0:
        _log(f"embedder already present ({dest.stat().st_size} bytes)")
        return
    _download(url, dest)


def main() -> int:
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    _log(f"weights dir: {WEIGHTS_DIR}")

    failures: list[str] = []
    for label, fn in (
        ("YOLO", _fetch_yolo),
        ("TAPNext", _fetch_tapnext),
        ("embedder", _fetch_embedder),
    ):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - report and continue
            _log(f"ERROR {label}: {exc}")
            failures.append(label)

    if failures:
        _log(f"completed with errors in: {', '.join(failures)}")
        return 1
    _log("all weights ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
