"""Serialization translators for sask HTTP response bodies.

All JSON serialization and resource-file reading for HTTP responses lives
here.  ``app.py`` must not call ``json.dumps`` on response bodies directly.
"""

import json

from .manifest import ResourceEntry


def health_to_json() -> bytes:
    """Serialize the health-check response to UTF-8 JSON bytes.

    Returns:
        Bytes representing ``{"status": "ok"}``.
    """
    return json.dumps({"status": "ok"}).encode()


def error_to_json(message: str) -> bytes:
    """Serialize an error message to UTF-8 JSON bytes.

    Args:
        message: Human-readable error description.

    Returns:
        Bytes representing ``{"error": <message>}``.
    """
    return json.dumps({"error": message}).encode()


def resource_to_bytes(entry: ResourceEntry) -> bytes:
    """Read a resource file from disk and return its raw bytes.

    Args:
        entry: The manifest entry describing the resource to read.

    Returns:
        Raw file bytes suitable for use as the HTTP response body.

    Raises:
        FileNotFoundError: If the resource file does not exist on disk.
    """
    if not entry.path.exists():
        raise FileNotFoundError(f"Resource file not found: {entry.path}")
    return entry.path.read_bytes()
