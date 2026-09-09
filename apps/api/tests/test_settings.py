"""Tests for the persisted settings API."""

from fastapi.testclient import TestClient

from app.models import DEFAULT_SETTINGS


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


def test_settings_persist_across_calls(client: TestClient) -> None:
    client.put("/api/settings", json={"values": {"confidenceThreshold": 0.6}})
    body = client.get("/api/settings").json()
    assert body["values"]["confidenceThreshold"] == 0.6
    assert body["revision"] >= 2
