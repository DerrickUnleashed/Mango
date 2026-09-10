"""Persisted track listing and tracker-selection tests."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient


def _upload(
    client: TestClient, data: bytes, name: str = "test.mp4", mime: str = "video/mp4"
) -> str:
    response = client.post(
        "/api/videos",
        files={"file": (name, data, mime)},
    )
    assert response.status_code == 201, response.text
    return response.json()["video"]["id"]


def _process(client: TestClient, video_id: str, **payload) -> dict:
    response = client.post(
        f"/api/videos/{video_id}/process",
        json={"inference_mode": "mock", **payload},
    )
    assert response.status_code == 200, response.text
    job_id = response.json()["id"]
    for _ in range(20):
        status = client.get(f"/api/jobs/{job_id}").json()
        if status["status"] in {"completed", "failed"}:
            return status
        time.sleep(0.2)
    raise AssertionError("processing did not finish")


def test_tracks_require_existing_video(client: TestClient) -> None:
    response = client.get("/api/videos/does-not-exist/tracks")
    assert response.status_code == 404
    assert response.json()["code"] == "video_not_found"


def test_tracks_empty_before_processing(client: TestClient, sample_video_bytes: bytes) -> None:
    video_id = _upload(client, sample_video_bytes)
    body = client.get(f"/api/videos/{video_id}/tracks").json()
    assert body == {"tracks": [], "total": 0}


def test_single_track_detail(client: TestClient, sample_video_bytes: bytes) -> None:
    video_id = _upload(client, sample_video_bytes)
    body = client.get(f"/api/videos/{video_id}/tracks").json()
    assert body == {"tracks": [], "total": 0}
    _process(client, video_id, tracker="mock", max_frames=10)

    tracks = client.get(f"/api/videos/{video_id}/tracks").json()
    assert tracks["total"] >= 1
    track_id = tracks["tracks"][0]["trackId"]
    detail = client.get(f"/api/videos/{video_id}/tracks/{track_id}").json()
    assert detail["track"]["trackId"] == track_id
    assert detail["track"]["points"] == tracks["tracks"][0]["points"]

    missing = client.get(f"/api/videos/{video_id}/tracks/9999")
    assert missing.status_code == 404
    assert missing.json()["code"] == "track_not_found"


def test_processing_with_bytetrack_tracker(client: TestClient, sample_video_bytes: bytes) -> None:
    video_id = _upload(client, sample_video_bytes)
    final = _process(client, video_id, tracker="bytetrack", max_frames=15)
    assert final["status"] == "completed", final

    tracks = client.get(f"/api/videos/{video_id}/tracks").json()
    assert tracks["total"] >= 1
    track = tracks["tracks"][0]
    assert track["status"] == "active"
    assert track["trackId"] == 1


def test_reprocessing_replaces_previous_tracks(
    client: TestClient, sample_video_bytes: bytes
) -> None:
    video_id = _upload(client, sample_video_bytes)
    _process(client, video_id, tracker="mock", max_frames=5)
    first = client.get(f"/api/videos/{video_id}/tracks").json()
    assert first["total"] >= 1
    first_ids = {t["id"] for t in first["tracks"]}

    _process(client, video_id, tracker="bytetrack", max_frames=5)
    second = client.get(f"/api/videos/{video_id}/tracks").json()
    assert second["total"] >= 1
    second_ids = {t["id"] for t in second["tracks"]}
    assert first_ids.isdisjoint(second_ids)


def test_identities_require_existing_video(client: TestClient) -> None:
    response = client.get("/api/videos/does-not-exist/identities")
    assert response.status_code == 404
    assert response.json()["code"] == "video_not_found"


def test_identities_empty_before_processing(client: TestClient, sample_video_bytes: bytes) -> None:
    video_id = _upload(client, sample_video_bytes)
    body = client.get(f"/api/videos/{video_id}/identities").json()
    assert body == {"identities": [], "total": 0}


def test_processing_persists_identities(client: TestClient, sample_video_bytes: bytes) -> None:
    video_id = _upload(client, sample_video_bytes)
    final = _process(client, video_id, tracker="mock", max_frames=30)
    assert final["status"] == "completed", final

    identities = client.get(f"/api/videos/{video_id}/identities").json()
    assert identities["total"] >= 1
    first = identities["identities"][0]
    assert first["identityId"] == 1
    assert first["observationCount"] >= 1
    assert first["videoId"] == video_id
    assert len(first["prototype"]) > 0


def test_processing_with_bytetrack_tracker_populates_last_track_id(
    client: TestClient, sample_video_bytes: bytes
) -> None:
    video_id = _upload(client, sample_video_bytes)
    final = _process(client, video_id, tracker="bytetrack", max_frames=15)
    assert final["status"] == "completed", final

    identities = client.get(f"/api/videos/{video_id}/identities").json()
    assert identities["total"] >= 1
    assert identities["identities"][0]["lastTrackId"] is not None


def test_identity_detail_endpoint(client: TestClient, sample_video_bytes: bytes) -> None:
    video_id = _upload(client, sample_video_bytes)
    _process(client, video_id, tracker="mock", max_frames=15)
    identity_id = client.get(f"/api/videos/{video_id}/identities").json()["identities"][0][
        "identityId"
    ]
    detail = client.get(f"/api/videos/{video_id}/identities/{identity_id}")
    assert detail.status_code == 200
    assert detail.json()["identityId"] == identity_id

    missing = client.get(f"/api/videos/{video_id}/identities/99999")
    assert missing.status_code == 404
    assert missing.json()["code"] == "identity_not_found"


def test_reid_events_empty_before_processing(client: TestClient, sample_video_bytes: bytes) -> None:
    video_id = _upload(client, sample_video_bytes)
    body = client.get(f"/api/videos/{video_id}/reid-events").json()
    assert body == {"events": [], "total": 0}


def test_reid_events_require_existing_video(client: TestClient) -> None:
    response = client.get("/api/videos/does-not-exist/reid-events")
    assert response.status_code == 404
    assert response.json()["code"] == "video_not_found"


def test_detections_empty_before_processing(client: TestClient, sample_video_bytes: bytes) -> None:
    video_id = _upload(client, sample_video_bytes)
    body = client.get(f"/api/videos/{video_id}/detections").json()
    assert body == {"detections": [], "total": 0}


def test_detections_require_existing_video(client: TestClient) -> None:
    response = client.get("/api/videos/does-not-exist/detections")
    assert response.status_code == 404
    assert response.json()["code"] == "video_not_found"


def test_motion_empty_before_processing(client: TestClient, sample_video_bytes: bytes) -> None:
    video_id = _upload(client, sample_video_bytes)
    body = client.get(f"/api/videos/{video_id}/motion").json()
    assert body == {"estimate": None, "compensationApplied": None}


def test_processing_persists_static_motion(client: TestClient, sample_video_bytes: bytes) -> None:
    video_id = _upload(client, sample_video_bytes)
    final = _process(client, video_id, tracker="mock", max_frames=15)
    assert final["status"] == "completed", final

    body = client.get(f"/api/videos/{video_id}/motion").json()
    assert body["compensationApplied"] is False
    estimate = body["estimate"]
    assert estimate is not None
    assert estimate["source"] == "static"
    assert estimate["dxPerFrame"] == 0.0
    assert estimate["dyPerFrame"] == 0.0
    assert estimate["framesAnalyzed"] == 15


def test_processing_with_drift_compensation(client: TestClient, sample_video_bytes: bytes) -> None:
    video_id = _upload(client, sample_video_bytes)
    final = _process(
        client,
        video_id,
        tracker="mock",
        max_frames=15,
        camera_motion="drift",
    )
    assert final["status"] == "completed", final

    body = client.get(f"/api/videos/{video_id}/motion").json()
    estimate = body["estimate"]
    assert estimate is not None
    assert estimate["source"] == "mock-drift"
    assert estimate["dxPerFrame"] == 0.5
    assert estimate["dyPerFrame"] == 0.2
    assert body["compensationApplied"] is True


def test_motion_requires_existing_video(client: TestClient) -> None:
    response = client.get("/api/videos/does-not-exist/motion")
    assert response.status_code == 404
    assert response.json()["code"] == "video_not_found"


def test_analytics_require_existing_video(client: TestClient) -> None:
    response = client.get("/api/videos/does-not-exist/analytics")
    assert response.status_code == 404
    assert response.json()["code"] == "video_not_found"


def test_analytics_empty_before_processing(client: TestClient, sample_video_bytes: bytes) -> None:
    video_id = _upload(client, sample_video_bytes)
    body = client.get(f"/api/videos/{video_id}/analytics").json()
    assert body == {"summary": None}


def test_processing_exposes_analytics(client: TestClient, sample_video_bytes: bytes) -> None:
    video_id = _upload(client, sample_video_bytes)
    final = _process(client, video_id, tracker="mock", max_frames=15)
    assert final["status"] == "completed", final

    body = client.get(f"/api/videos/{video_id}/analytics").json()
    summary = body["summary"]
    assert summary is not None
    assert summary["videoId"] == video_id
    assert summary["totalFrames"] >= 15  # full video, not the processed cap
    assert summary["totalFruitDetections"] > 0
    assert summary["uniqueIdentities"] >= 1
    assert summary["activeTracks"] >= 1
    assert summary["recoveredIdentities"] >= 0
    assert 0.0 <= summary["avgConfidence"] <= 1.0
    assert len(summary["fruitPerFrame"]) == summary["totalFrames"]
    assert len(summary["tracksPerFrame"]) == summary["totalFrames"]
    assert summary["confidenceDistribution"]
    assert summary["processingSeconds"] >= 0.0


def test_processing_job_exposes_pipeline_config(
    client: TestClient, sample_video_bytes: bytes
) -> None:
    video_id = _upload(client, sample_video_bytes)
    response = client.post(
        f"/api/videos/{video_id}/process",
        json={
            "inference_mode": "mock",
            "tracker": "bytetrack",
            "camera_motion": "drift",
            "confidence_threshold": 0.42,
            "reid_threshold": 0.5,
            "memory_update_rate": 0.1,
            "tracker_match_threshold": 200.0,
            "tracker_buffer_frames": 20,
            "max_frames": 6,
        },
    )
    assert response.status_code == 200, response.text
    job_id = response.json()["id"]

    final = client.get(f"/api/jobs/{job_id}").json()
    assert final["status"] in {"queued", "running", "completed", "failed"}
    cfg = final["config"]
    assert cfg is not None
    assert cfg["reid_threshold"] == 0.5
    assert cfg["memory_update_rate"] == 0.1
    assert cfg["confidence_threshold"] == 0.42
    assert cfg["tracker"] == "bytetrack"
    assert cfg["camera_motion"] == "drift"
    assert cfg["tracker_match_threshold"] == 200.0
    assert cfg["tracker_buffer_frames"] == 20
    assert cfg["max_frames"] == 6

    video_body = client.get(f"/api/videos/{video_id}").json()
    job_on_video = video_body["processingJob"]
    assert job_on_video is not None
    assert job_on_video["config"] == cfg


def test_processing_persists_detections(client: TestClient, sample_video_bytes: bytes) -> None:
    video_id = _upload(client, sample_video_bytes)
    final = _process(client, video_id, tracker="mock", max_frames=15)
    assert final["status"] == "completed", final

    all_dets = client.get(f"/api/videos/{video_id}/detections").json()
    assert all_dets["total"] >= 5
    first = all_dets["detections"][0]
    assert set(first) >= {"frameId", "trackId", "bbox", "confidence", "classLabel"}
    assert len(first["bbox"]) == 4

    frame_dets = client.get(f"/api/videos/{video_id}/detections", params={"frame_id": 0}).json()
    assert frame_dets["total"] >= 1
    assert all(d["frameId"] == 0 for d in frame_dets["detections"])


def test_identity_observations_persisted(client: TestClient, sample_video_bytes: bytes) -> None:
    video_id = _upload(client, sample_video_bytes)
    final = _process(client, video_id, tracker="mock", max_frames=20)
    assert final["status"] == "completed", final

    identities = client.get(f"/api/videos/{video_id}/identities").json()
    assert identities["total"] >= 1
    identity_id = identities["identities"][0]["identityId"]

    body = client.get(f"/api/videos/{video_id}/identities/{identity_id}/observations").json()
    assert body["total"] >= 1
    first = body["observations"][0]
    assert set(first) >= {"frameId", "trackId", "bbox", "confidence", "isOccluded"}
    assert 0.0 <= first["qualityAfter"] <= 1.0
    frame_ids = [o["frameId"] for o in body["observations"]]
    assert frame_ids == sorted(frame_ids)


def test_identity_observations_require_existing_id(
    client: TestClient, sample_video_bytes: bytes
) -> None:
    video_id = _upload(client, sample_video_bytes)
    final = _process(client, video_id, tracker="mock", max_frames=20)
    assert final["status"] == "completed", final

    missing = client.get(f"/api/videos/{video_id}/identities/99999/observations")
    assert missing.status_code == 404
    assert missing.json()["code"] == "identity_not_found"
