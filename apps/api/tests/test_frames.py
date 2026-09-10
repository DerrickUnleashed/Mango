"""Frame extraction endpoint tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

JPEG_MAGIC = b"\xff\xd8\xff"


def _upload(
    client: TestClient, data: bytes, name: str = "test.mp4", mime: str = "video/mp4"
) -> str:
    response = client.post(
        "/api/videos",
        files={"file": (name, data, mime)},
    )
    assert response.status_code == 201, response.text
    return response.json()["video"]["id"]


def test_frame_requires_existing_video(client: TestClient) -> None:
    response = client.get("/api/videos/does-not-exist/frames/0")
    assert response.status_code == 404
    assert response.json()["code"] == "video_not_found"


def test_frame_out_of_range(client: TestClient, sample_video_bytes: bytes) -> None:
    video_id = _upload(client, sample_video_bytes)
    response = client.get(f"/api/videos/{video_id}/frames/999999")
    assert response.status_code == 404
    assert response.json()["code"] == "frame_not_found"

    negative = client.get(f"/api/videos/{video_id}/frames/-1")
    assert negative.status_code == 404


def test_frame_extraction_returns_jpeg(client: TestClient, sample_video_bytes: bytes) -> None:
    video_id = _upload(client, sample_video_bytes)
    response = client.get(f"/api/videos/{video_id}/frames/0")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content.startswith(JPEG_MAGIC)

    thumb = client.get(f"/api/videos/{video_id}/frames/0", params={"width": 40})
    assert thumb.status_code == 200
    assert thumb.content.startswith(JPEG_MAGIC)
    assert len(thumb.content) < len(response.content)


def test_frame_source_file_served(client: TestClient, sample_video_bytes: bytes) -> None:
    video_id = _upload(client, sample_video_bytes)
    response = client.get(f"/api/videos/{video_id}/file")
    assert response.status_code == 200
    assert response.content == sample_video_bytes


def test_frame_cache_serves_identical_bytes(client: TestClient, sample_video_bytes: bytes) -> None:
    video_id = _upload(client, sample_video_bytes)
    first = client.get(f"/api/videos/{video_id}/frames/0").content
    second = client.get(f"/api/videos/{video_id}/frames/0").content
    assert first == second


def test_frame_for_missing_video_file(client: TestClient, sample_video_bytes: bytes) -> None:
    video_id = _upload(client, sample_video_bytes)
    client.delete(f"/api/videos/{video_id}")
    response = client.get(f"/api/videos/{video_id}/frames/0")
    assert response.status_code == 404
    assert response.json()["code"] == "video_not_found"
