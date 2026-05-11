"""Tests for bearer-token authentication on the /resource endpoint."""


def test_missing_token_returns_401(client) -> None:
    """Request with no Authorization header returns 401."""
    response = client.get("/resource/image/splash")
    assert response.status_code == 401


def test_wrong_token_returns_401(client) -> None:
    """Request with an incorrect bearer token returns 401."""
    response = client.get(
        "/resource/image/splash",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 401


def test_malformed_auth_scheme_returns_401(client) -> None:
    """Request with a non-Bearer Authorization scheme returns 401."""
    response = client.get(
        "/resource/image/splash",
        headers={"Authorization": "Basic dXNlcjpwYXNz"},
    )
    assert response.status_code == 401


def test_valid_token_does_not_return_401(client, valid_token: str) -> None:
    """Request with the correct bearer token does not return 401."""
    response = client.get(
        "/resource/image/splash",
        headers={"Authorization": f"Bearer {valid_token}"},
    )
    assert response.status_code != 401


def test_401_body_is_json(client) -> None:
    """A 401 response body is JSON with an error key."""
    response = client.get("/resource/image/splash")
    data = response.get_json()
    assert data is not None
    assert "error" in data
