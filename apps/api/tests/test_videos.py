"""Video upload, CRUD, and processing flow tests."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient


def _upload(
    client: TestClient, data: bytes, name: str = "test.mp4", mime: str = "video/mp4"
) -> dict:
    response = client.post(
        "/api/videos",
        files={"file": (name, data, mime)},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_upload_video_and_list(client: TestClient, sample_video_bytes: bytes) -> None:
    body = _upload(client, sample_video_bytes)
    video = body["video"]
    assert video["status"] == "uploaded"
    assert video["mimeType"] == "video/mp4"
    assert video["width"] == 640
    assert video["height"] == 360
    assert video["fps"] == 30.0
    assert video["frameCount"] == 30

    listing = client.get("/api/videos").json()
    assert listing["total"] >= 1
    assert any(v["id"] == video["id"] for v in listing["videos"])


def test_upload_rejects_non_video(client: TestClient) -> None:
    response = client.post(
        "/api/videos",
        files={"file": ("notes.txt", b"not a video", "text/plain")},
    )
    assert response.status_code == 422
    assert response.json()["code"] in {"invalid_upload", "validation_error"}


def test_get_video_404(client: TestClient) -> None:
    response = client.get("/api/videos/does-not-exist")
    assert response.status_code == 404
    assert response.json()["code"] == "video_not_found"


def test_delete_video(client: TestClient, sample_video_bytes: bytes) -> None:
    video_id = _upload(client, sample_video_bytes)["video"]["id"]
    response = client.delete(f"/api/videos/{video_id}")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert client.get(f"/api/videos/{video_id}").status_code == 404


def test_full_processing_flow(client: TestClient, sample_video_bytes: bytes) -> None:
    video_id = _upload(client, sample_video_bytes)["video"]["id"]

    process_response = client.post(
        f"/api/videos/{video_id}/process",
        json={"inference_mode": "mock", "max_frames": 15},
    )
    assert process_response.status_code == 200
    job = process_response.json()
    assert job["inference_mode"] == "mock"

    job_id = job["id"]
    final = None
    for _ in range(20):
        status_response = client.get(f"/api/jobs/{job_id}")
        assert status_response.status_code == 200
        final = status_response.json()
        if final["status"] in {"completed", "failed"}:
            break
        time.sleep(0.2)

    assert final is not None
    assert final["status"] == "completed", final
    assert final["stage"] == "completed"
    assert final["progress"] == 100.0

    video = client.get(f"/api/videos/{video_id}").json()
    assert video["status"] == "processed"

    tracks = client.get(f"/api/videos/{video_id}/tracks").json()
    assert tracks["total"] >= 1
    for track in tracks["tracks"]:
        assert track["videoId"] == video_id
        assert track["points"], track
        for point in track["points"]:
            assert set(point) >= {"frameId", "bbox", "confidence", "isOccluded"}


def test_video_serves_latest_processing_job(client: TestClient, sample_video_bytes: bytes) -> None:
    video_id = _upload(client, sample_video_bytes)["video"]["id"]

    def _run() -> dict:
        process_response = client.post(
            f"/api/videos/{video_id}/process",
            json={"inference_mode": "mock", "max_frames": 4},
        )
        assert process_response.status_code == 200
        job = process_response.json()
        final = None
        for _ in range(20):
            final = client.get(f"/api/jobs/{job['id']}").json()
            if final["status"] in {"completed", "failed"}:
                break
            time.sleep(0.2)
        assert final is not None and final["status"] == "completed", final
        return final

    first = _run()
    second = _run()
    assert first["job_id"] != second["job_id"]

    video = client.get(f"/api/videos/{video_id}").json()
    assert video["processingJob"] is not None
    assert video["processingJob"]["id"] == second["job_id"]
    assert video["processingJob"]["config"] == second["config"]


def test_process_unknown_video_404(client: TestClient) -> None:
    response = client.post(
        "/api/videos/missing/process",
        json={"inference_mode": "mock"},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "video_not_found"


def test_process_rejects_active_duplicate_job(
    client: TestClient, sample_video_bytes: bytes
) -> None:
    video_id = _upload(client, sample_video_bytes)["video"]["id"]

    from app.core.database import SessionLocal
    from app.models import ProcessingJob, ProcessingStage, ProcessingStatus

    with SessionLocal() as db:
        db.add(
            ProcessingJob(
                id="active-job-1",
                video_id=video_id,
                status=ProcessingStatus.RUNNING,
                stage=ProcessingStage.DETECTING,
                inference_mode="mock",
            )
        )
        db.commit()

    response = client.post(
        f"/api/videos/{video_id}/process",
        json={"inference_mode": "mock"},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "already_processing"
