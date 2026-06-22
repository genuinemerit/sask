"""Session-scoped fixtures for the live-deployment acceptance suite (SPEC-024).

Excluded from the default `pytest`/`pytest tests/` run (see pyproject.toml's
norecursedirs) — these tests hit the real network. Run explicitly:

    .venv/bin/pytest tests/acceptance/
"""

from __future__ import annotations

import os

import pytest

_DEFAULT_BASE_URL = "https://sask.davidstitt.net"


@pytest.fixture(scope="session")
def base_url() -> str:
    return os.environ.get("SASK_BASE_URL", _DEFAULT_BASE_URL)
