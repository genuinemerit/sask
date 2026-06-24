"""Timestamp helpers."""

from __future__ import annotations

from datetime import UTC, datetime


def create_iso_timestamp() -> str:
    """Return the current UTC timestamp in ISO 8601 format, millisecond precision."""
    return datetime.now(UTC).isoformat(timespec="milliseconds")
