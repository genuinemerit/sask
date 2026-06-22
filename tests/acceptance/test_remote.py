"""Acceptance tests against the real, deployed sask service (SPEC-024).

Uses `requests` against the live HTTPS endpoint, not Flask's test client —
some defects (a Caddyfile misconfiguration, a missing environment variable,
a TLS chain issue) are only visible through the full deployed stack. No
token/auth fixture: the app is public (DD-0014 decision #7).
"""

from __future__ import annotations

import requests

_EXPECTED_PULSE = "104548096103"


def test_health_returns_200(base_url: str) -> None:
    resp = requests.get(f"{base_url}/health", timeout=10)
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_tls_certificate_is_valid(base_url: str) -> None:
    # requests verifies the TLS chain by default; a successful response
    # without disabling verification *is* the test.
    resp = requests.get(f"{base_url}/health", timeout=10)
    assert resp.status_code == 200


def test_root_page_renders_expected_value(base_url: str) -> None:
    resp = requests.get(base_url, timeout=10)
    assert resp.status_code == 200
    assert _EXPECTED_PULSE in resp.text
