"""Tests for the Celery job queue integration."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.services.celery_app import run_processing_sync, run_video_processing
from app.services.processing import PipelineConfig


def _upload(
    client: TestClient, data: bytes, name: str = "queue.mp4", mime: str = "video/mp4"
) -> str:
    response = client.post("/api/videos", files={"file": (name, data, mime)})
    assert response.status_code == 201, response.text
    return response.json()["video"]["id"]


def _start(client: TestClient, video_id: str) -> dict:
    response = client.post(f"/api/videos/{video_id}/process", json={"inference_mode": "mock"})
    assert response.status_code == 200, response.text
    return client.get(f"/api/jobs/{response.json()['id']}").json()


def test_process_video_uses_in_process_path_without_broker(
    client: TestClient,
    sample_video_bytes: bytes,
    monkeypatch,
) -> None:
    import app.core.config as config_mod

    monkeypatch.setattr(config_mod.settings, "celery_broker_url", None)
    enqueued: list = []
    import app.routers.videos as videos_mod

    monkeypatch.setattr(videos_mod, "enqueue_video_processing", lambda *a, **k: enqueued.append(a))

    video_id = _upload(client, sample_video_bytes)
    job = _start(client, video_id)
    assert job["status"] in {"completed", "processing", "queued", "running", "failed"}
    for _ in range(20):
        job = client.get(f"/api/jobs/{job['job_id']}").json()
        if job["status"] in {"completed", "failed"}:
            break
        time.sleep(0.2)
    assert job["status"] == "completed", job
    assert enqueued == []


def test_process_video_enqueues_celery_when_broker_configured(
    client: TestClient,
    sample_video_bytes: bytes,
    monkeypatch,
) -> None:
    import app.core.config as config_mod

    monkeypatch.setattr(config_mod.settings, "celery_broker_url", "memory://")
    enqueued: list = []
    import app.routers.videos as videos_mod

    monkeypatch.setattr(videos_mod, "enqueue_video_processing", lambda *a, **k: enqueued.append(a))

    video_id = _upload(client, sample_video_bytes)
    job = _start(client, video_id)
    assert job["status"] == "queued"
    assert len(enqueued) == 1
    job_id, video_arg, config = enqueued[0]
    assert job_id == job["job_id"]
    assert video_arg == video_id
    assert config["inference_mode"] == "mock"
    assert "reid_threshold" in config


def test_run_video_processing_task_completes_job(
    client: TestClient, sample_video_bytes: bytes
) -> None:
    video_id = _upload(client, sample_video_bytes)
    job = _start(client, video_id)

    run_video_processing(job["job_id"], video_id, {"inference_mode": "mock", "max_frames": 10})

    final = client.get(f"/api/jobs/{job['job_id']}").json()
    assert final["status"] == "completed", final
    assert final["config"]["max_frames"] == 10
    assert final["stage"] == "completed"


def test_run_processing_sync_is_idempotent_for_missing_job(
    client: TestClient, sample_video_bytes: bytes
) -> None:
    run_processing_sync("does-not-exist", "also-missing", PipelineConfig())
    assert client.get("/api/jobs/does-not-exist").status_code == 404
