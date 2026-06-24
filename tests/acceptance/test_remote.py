"""Acceptance tests against the real, deployed sask service (SPEC-024, SPEC-027).

Uses `requests` against the live HTTPS endpoint, not Flask's test client —
some defects (a Caddyfile misconfiguration, a missing environment variable,
a TLS chain issue) are only visible through the full deployed stack. No
token/auth fixture: the app is public (DD-0014 decision #7).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import requests

_EXPECTED_PULSE = "104548096103"

# A known catalog entry (config/asset_catalog_data.toml) and its committed
# local source file, for the SPEC-027 byte-identity check — the
# deployed-pipeline analogue of sask-proto's own test_image_bytes_match_local.
_KNOWN_ASSET_KIND_ID = ("image", "splash.bg")
_KNOWN_ASSET_LOCAL_PATH = (
    Path(__file__).parent.parent.parent
    / "assets"
    / "v0"
    / "image"
    / "splash.default.1920x1080.6389524a.webp"
)


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


def test_asset_bytes_match_local(base_url: str) -> None:
    kind, asset_id = _KNOWN_ASSET_KIND_ID
    resp = requests.get(f"{base_url}/asset/{kind}/{asset_id}", timeout=10)
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "image/webp"
    local_sha256 = hashlib.sha256(_KNOWN_ASSET_LOCAL_PATH.read_bytes()).hexdigest()
    remote_sha256 = hashlib.sha256(resp.content).hexdigest()
    assert remote_sha256 == local_sha256


def test_unknown_asset_returns_404(base_url: str) -> None:
    resp = requests.get(f"{base_url}/asset/image/does-not-exist", timeout=10)
    assert resp.status_code == 404
