"""Tests for the /health endpoint."""


def test_health_returns_200(client) -> None:
    """GET /health returns HTTP 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_content_type_is_json(client) -> None:
    """GET /health sets Content-Type to application/json."""
    response = client.get("/health")
    assert "application/json" in response.content_type


def test_health_body_is_ok(client) -> None:
    """GET /health response body is {"status": "ok"}."""
    response = client.get("/health")
    assert response.get_json() == {"status": "ok"}


def test_health_requires_no_auth(client) -> None:
    """GET /health succeeds with no Authorization header."""
    response = client.get("/health")
    assert response.status_code == 200
