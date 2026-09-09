"""Tests for the evaluation experiments API."""

import time

from fastapi.testclient import TestClient


def _run_experiment(client: TestClient, tracker: str = "mock") -> dict:
    response = client.post(
        "/api/experiments",
        json={"name": f"test-{tracker}", "tracker": tracker, "num_frames": 50},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_experiments_empty_by_default(client: TestClient) -> None:
    body = client.get("/api/experiments").json()
    assert body == {"experiments": [], "total": 0}


def test_create_experiment_runs_and_scores(client: TestClient) -> None:
    experiment = _run_experiment(client, tracker="mock")
    assert experiment["status"] == "completed", experiment
    assert experiment["tracker"] == "mock"
    assert experiment["numFrames"] == 50
    assert experiment["createdAt"] is not None
    assert experiment["metrics"] is not None
    assert 0.0 <= experiment["metrics"]["idf1"] <= 1.0
    assert experiment["metrics"]["countMae"] >= 0.0
    assert experiment["metrics"]["idSwitches"] >= 0


def test_listing_experiments_returns_newest_first(client: TestClient) -> None:
    before = client.get("/api/experiments").json()["total"]
    a = _run_experiment(client, tracker="bytetrack")
    time.sleep(0.01)
    b = _run_experiment(client, tracker="mock")
    body = client.get("/api/experiments").json()
    assert body["total"] == before + 2
    assert body["experiments"][0]["id"] == b["id"]
    assert body["experiments"][1]["id"] == a["id"]


def test_experiment_detail_and_metrics(client: TestClient) -> None:
    experiment = _run_experiment(client)
    body = client.get(f"/api/experiments/{experiment['id']}").json()
    assert body["id"] == experiment["id"]
    assert body["metrics"]["idf1"] == experiment["metrics"]["idf1"]


def test_experiment_404(client: TestClient) -> None:
    body = client.get("/api/experiments/does-not-exist")
    assert body.status_code == 404
    assert body.json()["code"] == "experiment_not_found"


def test_delete_experiment(client: TestClient) -> None:
    experiment = _run_experiment(client)
    before = client.get("/api/experiments").json()["total"]
    response = client.delete(f"/api/experiments/{experiment['id']}")
    assert response.status_code == 200
    body = client.get("/api/experiments").json()
    assert body["total"] == before - 1


def test_invalid_tracker_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/experiments",
        json={"tracker": "not-a-tracker", "num_frames": 30},
    )
    assert response.status_code == 422
