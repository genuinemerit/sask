"""Tests for the /resource/<kind>/<id> endpoint."""

import pytest


@pytest.fixture
def auth(valid_token: str) -> dict[str, str]:
    """Return an Authorization header dict for the valid test token.

    Args:
        valid_token: The bearer token accepted by the test server.

    Returns:
        A headers dict suitable for passing to the test client.
    """
    return {"Authorization": f"Bearer {valid_token}"}


def test_image_returns_200(client, auth) -> None:
    """GET /resource/image/splash with valid token returns 200."""
    response = client.get("/resource/image/splash", headers=auth)
    assert response.status_code == 200


def test_image_content_type(client, auth) -> None:
    """GET /resource/image/splash returns image/png Content-Type."""
    response = client.get("/resource/image/splash", headers=auth)
    assert response.content_type == "image/png"


def test_json_returns_200(client, auth) -> None:
    """GET /resource/json/scenario-001 with valid token returns 200."""
    response = client.get("/resource/json/scenario-001", headers=auth)
    assert response.status_code == 200


def test_json_content_type(client, auth) -> None:
    """GET /resource/json/scenario-001 returns application/json Content-Type."""
    response = client.get("/resource/json/scenario-001", headers=auth)
    assert "application/json" in response.content_type


def test_audio_loop_returns_200(client, auth) -> None:
    """GET /resource/audio/ambient-loop with valid token returns 200."""
    response = client.get("/resource/audio/ambient-loop", headers=auth)
    assert response.status_code == 200


def test_audio_loop_content_type(client, auth) -> None:
    """GET /resource/audio/ambient-loop returns audio/mpeg Content-Type."""
    response = client.get("/resource/audio/ambient-loop", headers=auth)
    assert response.content_type == "audio/mpeg"


def test_audio_video_returns_200(client, auth) -> None:
    """GET /resource/audio/ambient-video with valid token returns 200."""
    response = client.get("/resource/audio/ambient-video", headers=auth)
    assert response.status_code == 200


def test_audio_video_content_type(client, auth) -> None:
    """GET /resource/audio/ambient-video returns video/mp4 Content-Type."""
    response = client.get("/resource/audio/ambient-video", headers=auth)
    assert response.content_type == "video/mp4"


def test_unknown_id_returns_404(client, auth) -> None:
    """GET /resource/image/<unknown-id> with valid token returns 404."""
    response = client.get("/resource/image/does-not-exist", headers=auth)
    assert response.status_code == 404


def test_unknown_kind_returns_404(client, auth) -> None:
    """GET /resource/<unknown-kind>/splash with valid token returns 404."""
    response = client.get("/resource/video/splash", headers=auth)
    assert response.status_code == 404


def test_resource_body_is_non_empty(client, auth) -> None:
    """A successful resource response has a non-empty body."""
    response = client.get("/resource/image/splash", headers=auth)
    assert len(response.data) > 0


def test_404_body_is_json(client, auth) -> None:
    """A 404 response body is JSON with an error key."""
    response = client.get("/resource/image/does-not-exist", headers=auth)
    data = response.get_json()
    assert data is not None
    assert "error" in data
