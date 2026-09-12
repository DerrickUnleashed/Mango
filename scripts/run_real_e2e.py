"""End-to-end real-mode run of the video analysis pipeline via the HTTP surface.

Drives the real FastAPI app (via TestClient) against a real input video:
upload -> process (inference_mode="real", bytetrack, optional frame cap) ->
query persisted detections/tracks/identities/re-id/analytics. Prints a
compact JSON summary. Exits non-zero if the job fails or produces no
detections (unless --allow-empty is given).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="Path to the input video file")
    parser.add_argument(
        "--max-frames", type=int, default=0, help="Cap on processed frames (0 = all)"
    )
    parser.add_argument("--model-path", default=None, help="YOLO weights override")
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Exit 0 even when the pipeline produces no detections",
    )
    args = parser.parse_args()

    if not args.video.is_file():
        print(f"video not found: {args.video}", file=sys.stderr)
        return 2

    tmp = tempfile.mkdtemp(prefix="orchardvision-e2e-")
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/e2e.db"
    os.environ["UPLOAD_DIR"] = f"{tmp}/uploads"
    os.environ["PROCESSED_DIR"] = f"{tmp}/processed"
    os.environ["AUTO_CREATE_TABLES"] = "true"

    from app.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        with args.video.open("rb") as handle:
            response = client.post(
                "/api/videos",
                files={"file": (args.video.name, handle, "video/mp4")},
            )
        response.raise_for_status()
        video = response.json()["video"]
        video_id = video["id"]

        request: dict = {
            "inference_mode": "real",
            "tracker": "bytetrack",
            "camera_motion": "static",
        }
        if args.max_frames:
            request["max_frames"] = args.max_frames
        if args.model_path:
            request["model_path"] = args.model_path

        started = time.perf_counter()
        response = client.post(f"/api/videos/{video_id}/process", json=request)
        response.raise_for_status()
        job = response.json()
        elapsed = time.perf_counter() - started

        job_id = job.get("id")
        status = job.get("status")

        import time as _time

        for _ in range(60):
            if status in ("completed", "failed", "cancelled"):
                break
            _time.sleep(2.0)
            refreshed = client.get(f"/api/jobs/{job_id}").json()
            status = refreshed.get("job", refreshed).get("status", status)

        def get(path: str) -> list | dict | None:
            res = client.get(f"/api/videos/{video_id}{path}")
            if res.status_code != 200:
                return None
            body = res.json()
            if isinstance(body, dict):
                list_value = next(
                    (value for key, value in body.items() if key != "total" and isinstance(value, list)),
                    None,
                )
                return list_value if list_value is not None else body
            return body

        detections = get("/detections") or []
        tracks = get("/tracks") or []
        identities = get("/identities") or []
        reid = get("/reid-events") or []
        analytics = get("/analytics") or {}

        confs = [d.get("confidence", 0.0) for d in detections]
        summary = {
            "video": video_id,
            "filename": args.video.name,
            "frames_total": video.get("frameCount"),
            "job_status": status,
            "job_id": job_id,
            "processed_secs": round(elapsed, 2),
            "fps": round(video.get("frameCount", 0) / elapsed, 2) if elapsed else None,
            "detections": len(detections),
            "avg_confidence": round(sum(confs) / len(confs), 3) if confs else None,
            "tracks": len(tracks),
            "identities": len(identities),
            "reid_events": len(reid),
            "analytics": analytics,
        }
        print(json.dumps(summary, indent=2))

        if status not in ("completed", "done", "succeeded"):
            print(f"job did not complete: {status}", file=sys.stderr)
            return 1
        if not detections and not args.allow_empty:
            print("pipeline produced zero detections", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())