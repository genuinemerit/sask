"""Pytest suite for tools/helpers/match_semver.py."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "helpers"))
from match_semver import match_semver  # noqa: E402


# ── Happy path ──────────────────────────────────────────────────────────────


def test_basic_version():
    assert match_semver("1.2.3") is True


def test_zero_version():
    assert match_semver("0.0.0") is True


def test_multi_digit_components():
    assert match_semver("10.20.300") is True


def test_prerelease_and_build_metadata():
    assert match_semver("1.2.3-alpha.1+build.5") is True


def test_prerelease_only():
    assert match_semver("1.0.0-rc.1") is True


def test_build_metadata_only():
    assert match_semver("1.0.0+20130313144700") is True


# ── Unhappy path ────────────────────────────────────────────────────────────


def test_missing_patch_component():
    assert match_semver("1.2") is False


def test_extra_component():
    assert match_semver("1.2.3.4") is False


def test_leading_zero_in_major():
    assert match_semver("01.2.3") is False


def test_leading_zero_in_prerelease_numeric_identifier():
    assert match_semver("1.2.3-01") is False


def test_empty_string():
    assert match_semver("") is False


def test_non_numeric_component():
    assert match_semver("a.b.c") is False


def test_trailing_garbage():
    assert match_semver("1.2.3 ") is False
