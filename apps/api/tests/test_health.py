"""Health endpoint tests."""

from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "OrchardVision API"
    assert "version" in body


def test_root_returns_service_info(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "OrchardVision API"


def test_unknown_route_returns_structural_404(client: TestClient) -> None:
    response = client.get("/api/nonexistent")
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "not_found"
    assert isinstance(body["detail"], str)


def test_security_headers_set(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
