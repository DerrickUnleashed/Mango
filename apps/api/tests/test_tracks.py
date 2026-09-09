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
