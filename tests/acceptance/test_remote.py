"""Acceptance tests for the deployed sask service at the remote HTTPS endpoint.

These tests use the real service (not the Flask test client) and require:
  - A provisioned droplet running the deployed service.
  - ~/.config/sask/tokens.toml with at least one valid token.

Run with:
    poetry run pytest tests/acceptance/ -v
"""

import hashlib
from pathlib import Path

import requests

_PROJECT_ROOT = Path(__file__).parent.parent.parent


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health_returns_200(base_url: str) -> None:
    """GET /health returns 200 with no authentication required."""
    response = requests.get(f"{base_url}/health")
    assert response.status_code == 200


def test_health_body(base_url: str) -> None:
    """GET /health returns {\"status\": \"ok\"}."""
    response = requests.get(f"{base_url}/health")
    assert response.json() == {"status": "ok"}


def test_tls_certificate_is_valid(base_url: str) -> None:
    """HTTPS connection succeeds without disabling certificate verification."""
    response = requests.get(f"{base_url}/health", verify=True)
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Authentication — unhappy paths
# ---------------------------------------------------------------------------


def test_missing_token_returns_401(base_url: str) -> None:
    """GET /resource without Authorization header returns 401."""
    response = requests.get(f"{base_url}/resource/json/scenario-001")
    assert response.status_code == 401


def test_bad_token_returns_401(base_url: str) -> None:
    """GET /resource with an invalid bearer token returns 401."""
    response = requests.get(
        f"{base_url}/resource/json/scenario-001",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Resource retrieval — happy paths
# ---------------------------------------------------------------------------


def test_image_returns_200(base_url: str, auth_headers: dict) -> None:
    """GET /resource/image/splash with valid token returns 200."""
    response = requests.get(f"{base_url}/resource/image/splash", headers=auth_headers)
    assert response.status_code == 200


def test_image_content_type(base_url: str, auth_headers: dict) -> None:
    """GET /resource/image/splash returns image/png content type."""
    response = requests.get(f"{base_url}/resource/image/splash", headers=auth_headers)
    assert response.headers["content-type"] == "image/png"


def test_json_returns_200(base_url: str, auth_headers: dict) -> None:
    """GET /resource/json/scenario-001 with valid token returns 200."""
    response = requests.get(
        f"{base_url}/resource/json/scenario-001", headers=auth_headers
    )
    assert response.status_code == 200


def test_json_content_type(base_url: str, auth_headers: dict) -> None:
    """GET /resource/json/scenario-001 returns application/json content type."""
    response = requests.get(
        f"{base_url}/resource/json/scenario-001", headers=auth_headers
    )
    assert "application/json" in response.headers["content-type"]


def test_audio_loop_returns_200(base_url: str, auth_headers: dict) -> None:
    """GET /resource/audio/ambient-loop with valid token returns 200."""
    response = requests.get(
        f"{base_url}/resource/audio/ambient-loop", headers=auth_headers
    )
    assert response.status_code == 200


def test_audio_loop_content_type(base_url: str, auth_headers: dict) -> None:
    """GET /resource/audio/ambient-loop returns audio/mpeg content type."""
    response = requests.get(
        f"{base_url}/resource/audio/ambient-loop", headers=auth_headers
    )
    assert response.headers["content-type"] == "audio/mpeg"


def test_audio_video_returns_200(base_url: str, auth_headers: dict) -> None:
    """GET /resource/audio/ambient-video with valid token returns 200."""
    response = requests.get(
        f"{base_url}/resource/audio/ambient-video", headers=auth_headers
    )
    assert response.status_code == 200


def test_audio_video_content_type(base_url: str, auth_headers: dict) -> None:
    """GET /resource/audio/ambient-video returns video/mp4 content type."""
    response = requests.get(
        f"{base_url}/resource/audio/ambient-video", headers=auth_headers
    )
    assert response.headers["content-type"] == "video/mp4"


# ---------------------------------------------------------------------------
# Resource retrieval — unhappy paths
# ---------------------------------------------------------------------------


def test_unknown_id_returns_404(base_url: str, auth_headers: dict) -> None:
    """GET /resource/json/<unknown-id> with valid token returns 404."""
    response = requests.get(
        f"{base_url}/resource/json/no-such-id", headers=auth_headers
    )
    assert response.status_code == 404


def test_unknown_kind_returns_404(base_url: str, auth_headers: dict) -> None:
    """GET /resource/<unknown-kind>/splash with valid token returns 404."""
    response = requests.get(
        f"{base_url}/resource/video/splash", headers=auth_headers
    )
    assert response.status_code == 404


def test_404_body_is_json_with_error_key(base_url: str, auth_headers: dict) -> None:
    """A 404 response body is JSON containing an 'error' key."""
    response = requests.get(
        f"{base_url}/resource/image/no-such-id", headers=auth_headers
    )
    data = response.json()
    assert data is not None
    assert "error" in data


# ---------------------------------------------------------------------------
# Byte identity
# ---------------------------------------------------------------------------


def test_image_bytes_match_local(base_url: str, auth_headers: dict) -> None:
    """Remote splash.png bytes are identical to the local resource file."""
    response = requests.get(f"{base_url}/resource/image/splash", headers=auth_headers)
    assert response.status_code == 200
    local_path = _PROJECT_ROOT / "resources" / "images" / "splash.png"
    local_hash = hashlib.sha256(local_path.read_bytes()).hexdigest()
    remote_hash = hashlib.sha256(response.content).hexdigest()
    assert local_hash == remote_hash, (
        f"sha256 mismatch: local={local_hash[:12]}… remote={remote_hash[:12]}…"
    )
