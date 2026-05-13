"""Pytest configuration for acceptance tests against the deployed remote endpoint.

Reads the bearer token from the developer's local tokens file so that tests
run against the real HTTPS service without hardcoding credentials.
"""

import tomllib
from pathlib import Path

import pytest

_TOKENS_PATH = Path.home() / ".config" / "sask" / "tokens.toml"
_BASE_URL = "https://sask.davidstitt.net"


def _read_first_token() -> str:
    """Read the first token value from the local tokens TOML file.

    Returns:
        The bearer token string.

    Raises:
        FileNotFoundError: If the tokens file does not exist.
        KeyError: If the file has no token entries.
    """
    with open(_TOKENS_PATH, "rb") as fh:
        data = tomllib.load(fh)
    return data["token"][0]["token"]


@pytest.fixture(scope="session")
def base_url() -> str:
    """Return the base URL of the deployed service.

    Returns:
        HTTPS base URL string (no trailing slash).
    """
    return _BASE_URL


@pytest.fixture(scope="session")
def token() -> str:
    """Return a valid bearer token from the local tokens file.

    Returns:
        Bearer token string.
    """
    return _read_first_token()


@pytest.fixture(scope="session")
def auth_headers(token: str) -> dict[str, str]:
    """Return an Authorization header dict for use with requests.

    Args:
        token: Bearer token from the local tokens file.

    Returns:
        Headers dict with Authorization key.
    """
    return {"Authorization": f"Bearer {token}"}
