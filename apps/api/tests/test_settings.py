"""Tests for the persisted settings API."""

from fastapi.testclient import TestClient

from app.models import DEFAULT_SETTINGS


def _upload_and_start(
    client: TestClient,
    data: bytes,
    name: str = "test.mp4",
    mime: str = "video/mp4",
) -> tuple[str, dict]:
    response = client.post(
        "/api/videos",
        files={"file": (name, data, mime)},
    )
    assert response.status_code == 201, response.text
    video_id = response.json()["video"]["id"]
    status = client.post(f"/api/videos/{video_id}/process", json={"inference_mode": "mock"})
    assert status.status_code == 200, status.text
    job = client.get(f"/api/jobs/{status.json()['id']}").json()
    return video_id, job


def test_get_settings_returns_defaults(client: TestClient) -> None:
    body = client.get("/api/settings").json()
    assert body["values"] == DEFAULT_SETTINGS
    assert body["revision"] >= 1


def test_update_settings_merges_partial(client: TestClient) -> None:
    body = client.put(
        "/api/settings",
        json={"values": {"confidenceThreshold": 0.5, "cameraMotionMode": "drift"}},
    ).json()
    assert body["values"]["confidenceThreshold"] == 0.5
    assert body["values"]["cameraMotionMode"] == "drift"
    assert body["values"]["reidThreshold"] == DEFAULT_SETTINGS["reidThreshold"]


def test_update_settings_ignores_unknown_keys(client: TestClient) -> None:
    client.put("/api/settings", json={"values": DEFAULT_SETTINGS})  # reset
    body = client.put("/api/settings", json={"values": {"bogus": 1}}).json()
    assert "bogus" not in body["values"]
    assert body["values"] == DEFAULT_SETTINGS


def test_boolean_settings_round_trip_as_booleans(client: TestClient) -> None:
    body = client.put(
        "/api/settings",
        json={"values": {"showTrackVisualizer": False, "showReidPanel": True}},
    ).json()
    assert body["values"]["showTrackVisualizer"] is False
    assert body["values"]["showReidPanel"] is True
    stored = client.get("/api/settings").json()
    assert stored["values"]["showTrackVisualizer"] is False
    assert stored["values"]["showReidPanel"] is True


def test_settings_persist_across_calls(client: TestClient) -> None:
    client.put("/api/settings", json={"values": {"confidenceThreshold": 0.6}})
    body = client.get("/api/settings").json()
    assert body["values"]["confidenceThreshold"] == 0.6
    assert body["revision"] >= 2


def test_processing_uses_stored_threshold_defaults(
    client: TestClient, sample_video_bytes: bytes
) -> None:
    client.put(
        "/api/settings",
        json={
            "values": {
                "confidenceThreshold": 0.55,
                "reidThreshold": 0.45,
                "memoryUpdateRate": 0.05,
                "trackerMatchThreshold": 240.0,
                "trackerBufferFrames": 12,
            }
        },
    )
    try:
        video_id, job = _upload_and_start(client, sample_video_bytes)
        cfg = job["config"]
        assert cfg["confidence_threshold"] == 0.55
        assert cfg["reid_threshold"] == 0.45
        assert cfg["memory_update_rate"] == 0.05
        assert cfg["tracker_match_threshold"] == 240.0
        assert cfg["tracker_buffer_frames"] == 12
        assert video_id  # keep video_id referenced
    finally:
        client.put("/api/settings", json={"values": DEFAULT_SETTINGS})  # reset
        if video_id:
            client.delete(f"/api/videos/{video_id}")
