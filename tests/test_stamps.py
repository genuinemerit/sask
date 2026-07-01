"""Pytest suite for tools/helpers/stamps.py."""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "helpers"))
from stamps import create_iso_timestamp  # noqa: E402

# millisecond precision, UTC offset "+00:00" (timespec="milliseconds" under
# datetime.now(UTC) never emits the "Z" shorthand)
_EXPECTED_SHAPE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}\+00:00$")


# ── Happy path ──────────────────────────────────────────────────────────────


def test_matches_expected_shape():
    assert _EXPECTED_SHAPE.match(create_iso_timestamp())


def test_round_trips_through_fromisoformat():
    stamp = create_iso_timestamp()
    parsed = datetime.fromisoformat(stamp)
    assert parsed.tzinfo is not None


def test_is_timezone_aware_utc():
    parsed = datetime.fromisoformat(create_iso_timestamp())
    assert parsed.utcoffset().total_seconds() == 0


def test_successive_calls_do_not_go_backwards():
    first = datetime.fromisoformat(create_iso_timestamp())
    second = datetime.fromisoformat(create_iso_timestamp())
    assert second >= first


# ── Unhappy path (shape must NOT admit looser formats) ──────────────────────


def test_does_not_emit_microsecond_precision():
    stamp = create_iso_timestamp()
    fractional = stamp.split(".", 1)[1]
    digits = fractional.split("+", 1)[0]
    assert len(digits) == 3


def test_does_not_emit_naive_datetime():
    stamp = create_iso_timestamp()
    assert stamp.endswith("+00:00")
