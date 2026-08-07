"""SPEC-040 tests — the structured API reference (DD-0027).

Covers:
  - /api/reference is served as HTML (default) and JSON (?format=json /
    Accept: application/json) from the committed static artifacts.
  - The JSON form is valid, parseable, and structurally complete: all five
    JSON-capable endpoints, their parameters, response shapes, the
    {id, label}/temporal-contract/error-envelope/negotiation/locale
    concepts, and the error-code catalog.
  - Examples parse and match the current response shapes.
  - The reference is English-only: unaffected by ?locale=.
  - The two-tier staleness check: deterministic tier fails on a stale
    artifact and passes on a fresh build; human-flag tier fails when a
    declared endpoint has no prose description.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "dev"))

import build_api_reference as bar  # noqa: E402
import check_api_reference_staleness as car  # noqa: E402

from sask.web import create_app  # noqa: E402

REAL_CONFIG = Path(__file__).parent.parent / "config"
API_REFERENCE_DIR = Path(__file__).parent.parent / "docs" / "api_reference"


@pytest.fixture(scope="module")
def app():
    return create_app(config_dir=REAL_CONFIG)


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


@pytest.fixture(scope="module")
def reference_json(client):
    resp = client.get("/api/reference?format=json")
    return resp.get_json()


# ── Served via DD-0026 negotiation ──────────────────────────────────────────


def test_html_default(client):
    resp = client.get("/api/reference")
    assert resp.status_code == 200
    assert "text/html" in resp.content_type
    assert b"sask API reference" in resp.data


def test_json_via_format_param(client):
    resp = client.get("/api/reference?format=json")
    assert resp.status_code == 200
    assert resp.content_type == "application/json"
    json.loads(resp.data)  # parses without error


def test_json_via_accept_header(client):
    resp = client.get("/api/reference", headers={"Accept": "application/json"})
    assert resp.status_code == 200
    assert resp.content_type == "application/json"


def test_html_when_accept_prefers_html(client):
    resp = client.get("/api/reference", headers={"Accept": "text/html"})
    assert "text/html" in resp.content_type


# ── Structural completeness ──────────────────────────────────────────────────


def test_covers_all_five_json_capable_endpoints(reference_json):
    assert set(reference_json["endpoints"]) == {
        "/",
        "/moons",
        "/planets",
        "/sky",
        "/ephemeris",
    }


def test_every_endpoint_has_description_and_parameters(reference_json):
    for path, entry in reference_json["endpoints"].items():
        assert entry["description"], path
        assert "parameters" in entry, path
        assert "response_shape" in entry, path
        assert "examples" in entry, path


def test_moment_bearing_endpoints_document_priority_and_branches(reference_json):
    for path in ("/moons", "/planets", "/sky", "/ephemeris"):
        mr = reference_json["endpoints"][path]["moment_resolution"]
        assert mr["priority"] == ["pulse", "astro_day", "fatunik_date", "terpin_date"]
        assert set(mr["branches"]) == set(mr["priority"])


def test_index_has_no_moment_resolution(reference_json):
    """/ is pulse-only (no moment_group) -- SPEC-041's preserved asymmetry."""
    assert "moment_resolution" not in reference_json["endpoints"]["/"]


def test_ephemeris_documents_throttle(reference_json):
    throttle = reference_json["endpoints"]["/ephemeris"]["throttle"]
    assert throttle["step_floor_minutes"] > 0
    assert throttle["range_cap_days"] > 0


def test_shared_parameters_include_format_and_locale(reference_json):
    names = {p["name"] for p in reference_json["shared_parameters"]}
    assert names == {"format", "locale"}


def test_concepts_present_and_nonempty(reference_json):
    for key in (
        "negotiation",
        "locale",
        "id_label",
        "temporal_contract",
        "error_envelope",
        "integration_guidance",
    ):
        assert reference_json[key], key


def test_locales_list_matches_served_locales(reference_json, app):
    cfg = app.config["SASK_CONFIG"]
    assert set(reference_json["locales"]) == set(cfg.i18n.locales)


def test_error_code_catalog_covers_known_codes(reference_json):
    codes = {c["code"] for c in reference_json["error_codes"]}
    # Representative sample spanning routes.py and params.py sources.
    assert {
        "unknown_param",
        "invalid_pulse_value",
        "invalid_profile",
        "invalid_format",
        "invalid_locale",
        "missing_moment_query",
        "missing_ephemeris_query",
        "ephemeris_range_invalid",
    } <= codes
    # Excludes codes reachable only from non-JSON-capable routes.
    assert "no_help_topic" not in codes
    assert "step_exceeds_range_download" not in codes
    for entry in reference_json["error_codes"]:
        assert entry["message_template"]


# ── Examples match current response shapes ──────────────────────────────────


def test_examples_have_basic_localized_and_error(reference_json):
    for path, entry in reference_json["endpoints"].items():
        assert set(entry["examples"]) == {"basic", "localized", "error"}


def test_basic_example_status_200_and_matches_response_shape(reference_json):
    for path, entry in reference_json["endpoints"].items():
        basic = entry["examples"]["basic"]
        assert basic["status"] == 200
        assert set(basic["body"].keys()) == set(entry["response_shape"].keys())


def test_error_example_status_400_with_envelope(reference_json):
    for path, entry in reference_json["endpoints"].items():
        err = entry["examples"]["error"]
        assert err["status"] == 400
        assert set(err["body"].keys()) == {"error"}
        assert "code" in err["body"]["error"]
        assert "message" in err["body"]["error"]


def test_localized_example_uses_es_es(reference_json):
    for path, entry in reference_json["endpoints"].items():
        assert "locale=es-ES" in entry["examples"]["localized"]["request"]
        assert entry["examples"]["localized"]["status"] == 200


# ── English-only (not affected by ?locale=) ─────────────────────────────────


def test_reference_ignores_locale_param(client):
    en = client.get("/api/reference?format=json").data
    es = client.get("/api/reference?format=json&locale=es-ES").data
    assert en == es


def test_reference_html_ignores_locale_param(client):
    en = client.get("/api/reference").data
    es = client.get("/api/reference?locale=es-ES").data
    assert en == es


# ── Staleness check: deterministic tier ─────────────────────────────────────


def test_check_clean_against_committed_artifacts():
    """The committed docs/api_reference/ artifacts, as they actually sit in
    the repo right now, must match a fresh build (this IS the pre-commit
    gate's own assertion, exercised directly)."""
    assert car.check() == []


def test_deterministic_tier_fails_on_stale_html(tmp_path, monkeypatch, app):
    monkeypatch.setattr(car, "OUT_DIR", tmp_path)
    _html, ref_json = bar.build_reference(app)
    (tmp_path / "index.html").write_text("stale content", encoding="utf-8")
    (tmp_path / "reference.json").write_text(ref_json, encoding="utf-8")
    errors = car.check()
    assert any("index.html" in e and "stale" in e for e in errors)


def test_deterministic_tier_fails_on_stale_json(tmp_path, monkeypatch, app):
    monkeypatch.setattr(car, "OUT_DIR", tmp_path)
    html_text, _ref_json = bar.build_reference(app)
    (tmp_path / "index.html").write_text(html_text, encoding="utf-8")
    (tmp_path / "reference.json").write_text("{}", encoding="utf-8")
    errors = car.check()
    assert any("reference.json" in e and "stale" in e for e in errors)


def test_missing_artifacts_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(car, "OUT_DIR", tmp_path)
    errors = car.check()
    assert any("does not exist" in e for e in errors)
    assert len(errors) == 2


def test_deterministic_tier_clean_after_fresh_build(tmp_path, monkeypatch, app):
    monkeypatch.setattr(car, "OUT_DIR", tmp_path)
    html_text, ref_json = bar.build_reference(app)
    (tmp_path / "index.html").write_text(html_text, encoding="utf-8")
    (tmp_path / "reference.json").write_text(ref_json, encoding="utf-8")
    assert car.check() == []


# ── Staleness check: human-flag tier ─────────────────────────────────────────


def _cfg_with_bogus_endpoint(app):
    cfg = app.config["SASK_CONFIG"]
    base_spec = cfg.endpoint_params.endpoints["/"]
    bogus_path = "/bogus-new-endpoint"
    new_endpoints = dict(cfg.endpoint_params.endpoints)
    new_endpoints[bogus_path] = dataclasses.replace(base_spec, path=bogus_path)
    new_declaration = dataclasses.replace(cfg.endpoint_params, endpoints=new_endpoints)
    return dataclasses.replace(cfg, endpoint_params=new_declaration), bogus_path


def test_human_flag_build_reference_raises_on_missing_description(app):
    # app is module-scoped and reused by other tests -- save/restore its
    # config rather than mutating it permanently.
    original_cfg = app.config["SASK_CONFIG"]
    new_cfg, _bogus_path = _cfg_with_bogus_endpoint(app)
    app.config["SASK_CONFIG"] = new_cfg
    try:
        with pytest.raises(KeyError, match="bogus-new-endpoint"):
            bar.build_reference(app)
    finally:
        app.config["SASK_CONFIG"] = original_cfg


def test_human_flag_via_check(monkeypatch, tmp_path):
    rigged_app = create_app(config_dir=REAL_CONFIG)
    new_cfg, bogus_path = _cfg_with_bogus_endpoint(rigged_app)
    rigged_app.config["SASK_CONFIG"] = new_cfg
    monkeypatch.setattr(car, "OUT_DIR", tmp_path)
    monkeypatch.setattr(car, "create_app", lambda config_dir: rigged_app)
    errors = car.check()
    assert len(errors) == 1
    assert "bogus-new-endpoint" in errors[0]
    assert "description" in errors[0]


# ── CLI wiring / pre-commit (structural, not behavioral duplication) ───────


def test_check_script_runs_clean_as_subprocess():
    import subprocess

    result = subprocess.run(
        [sys.executable, "tools/dev/check_api_reference_staleness.py"],
        cwd=str(Path(__file__).parent.parent),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
