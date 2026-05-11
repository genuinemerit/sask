"""Bearer-token authentication helpers for sask."""

import hmac
import os
from pathlib import Path

import tomllib

_DEFAULT_TOKENS_PATH = Path.home() / ".config" / "sask" / "tokens.toml"


def load_tokens(path: Path | None = None) -> list[dict[str, str]]:
    """Load authorized tokens from a TOML file.

    Args:
        path: Path to the tokens file. When ``None``, falls back to the
            ``SASK_TOKENS_PATH`` environment variable, then to
            ``~/.config/sask/tokens.toml``.

    Returns:
        List of token dicts; each dict has at least ``id`` and ``token`` keys.

    Raises:
        FileNotFoundError: If the resolved path does not exist.
        tomllib.TOMLDecodeError: If the file is not valid TOML.
    """
    if path is None:
        env = os.environ.get("SASK_TOKENS_PATH")
        path = Path(env) if env else _DEFAULT_TOKENS_PATH
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    return data.get("token", [])


def extract_bearer_token(authorization: str | None) -> str | None:
    """Extract the raw token from a Bearer Authorization header value.

    Args:
        authorization: The full value of the ``Authorization`` HTTP header,
            or ``None`` if the header was absent.

    Returns:
        The token string if the header is well-formed, otherwise ``None``.
    """
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":  # noqa: PLR2004
        return None
    return parts[1]


def is_valid_token(provided: str, tokens: list[dict[str, str]]) -> bool:
    """Return ``True`` if *provided* matches any authorized token.

    Comparison uses :func:`hmac.compare_digest` to resist timing attacks.

    Args:
        provided: The token string extracted from the request.
        tokens: Authorized token list from :func:`load_tokens`.

    Returns:
        ``True`` if *provided* matches at least one entry; ``False`` otherwise.
    """
    for entry in tokens:
        if hmac.compare_digest(provided, entry["token"]):
            return True
    return False
