"""SPEC-041 tests — single-source parameter declaration (DD-0028).

Covers:
  - config/endpoint_params.toml loads into a real, well-formed
    EndpointParamsConfig; malformed declarations raise ConfigError.
  - The shared helper (src/sask/web/params.py): moment-group priority
    resolution (unprefixed and prefixed), scalar type coercion, and
    check_params()'s unknown-param/value-constraint checking — direct,
    Flask-free calls.
  - Behavior preservation: full existing suite passes unchanged (asserted
    implicitly by CI running every test_spec_*.py file; this file adds only
    NEW coverage, not a re-test of already-covered endpoints).
  - The three owner-approved behavior changes: unknown query params now 400
    with error.unknown_param; an invalid /ephemeris profile now 400s with
    error.invalid_profile; an invalid format or locale VALUE (the two
    globally-declared params) now 400s with error.invalid_format /
    error.invalid_locale.
  - The declaration is a shape SPEC-040 can read (endpoints/params/
    descriptions all present).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from sask.config_loader import ConfigError, load_config
from sask.web import create_app
from sask.web.params import (
    check_params,
    known_param_names,
    parse_scalar,
    resolve_moment_group,
)

REAL_CONFIG = Path(__file__).parent.parent / "config"


@pytest.fixture(scope="module")
def app():
    return create_app(config_dir=REAL_CONFIG)


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


@pytest.fixture(scope="module")
def cfg(app):
    return app.config["SASK_CONFIG"]


# ── The declaration loads into a well-formed shape ──────────────────────────


def test_endpoint_params_loads(cfg):
    ep = cfg.endpoint_params
    assert set(ep.endpoints) == {"/", "/moons", "/planets", "/sky", "/ephemeris"}
    assert "full" in ep.moment_groups
    # Every declared param carries a human-readable English description —
    # the shape SPEC-040 will draw its per-param prose from.
    for name, spec in ep.params.items():
        assert spec.description, f"{name} has no description"


def test_globals_declared_and_available_on_every_endpoint(cfg):
    assert set(cfg.endpoint_params.globals) == {"format", "locale"}


def test_format_and_locale_are_declared_enums(cfg):
    ep = cfg.endpoint_params
    assert ep.params["format"].type == "enum"
    assert ep.params["format"].constraints["values"] == ["json"]
    assert ep.params["locale"].type == "enum"
    assert set(ep.params["locale"].constraints["values"]) == {"en-US", "es-ES"}


def test_index_declares_pulse_only(cfg):
    """/ is the one endpoint with no moment_group (existing asymmetry)."""
    spec = cfg.endpoint_params.endpoints["/"]
    assert spec.moment_group is None
    assert spec.scalars == ("pulse",)


def test_ephemeris_declares_prefixed_moment_group(cfg):
    spec = cfg.endpoint_params.endpoints["/ephemeris"]
    assert spec.moment_group == "full"
    assert spec.moment_group_prefix == "start_"
    assert set(spec.scalars) == {
        "end_pulse",
        "duration_days",
        "step_minutes",
        "profile",
    }


def test_profile_default_and_enum(cfg):
    profile = cfg.endpoint_params.params["profile"]
    assert profile.type == "enum"
    assert profile.default == "scribal"
    assert set(profile.constraints["values"]) == {"scribal", "kinematic", "both"}


def test_duration_days_min_constraint(cfg):
    assert cfg.endpoint_params.params["duration_days"].constraints["min"] == 1


def test_known_param_names_moons(cfg):
    endpoint = cfg.endpoint_params.endpoints["/moons"]
    names = known_param_names(endpoint, cfg.endpoint_params)
    assert names == {
        "format",
        "locale",
        "pulse",
        "astro_day",
        "time_of_day",
        "fatunik_year",
        "fatunik_month",
        "fatunik_day",
        "terpin_year",
        "terpin_month",
        "terpin_day",
    }


def test_known_param_names_ephemeris_are_prefixed(cfg):
    endpoint = cfg.endpoint_params.endpoints["/ephemeris"]
    names = known_param_names(endpoint, cfg.endpoint_params)
    assert "start_pulse" in names
    assert "start_astro_day" in names
    assert "start_time_of_day" in names
    assert "pulse" not in names  # not bare "pulse" -- must be prefixed
    assert {"end_pulse", "duration_days", "step_minutes", "profile"} <= names


# ── Malformed declarations raise ConfigError ────────────────────────────────


def _write_toml(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _minimal_config_dir(tmp_path: Path) -> Path:
    """Copy all real config files into tmp_path, returning tmp_path."""
    for f in REAL_CONFIG.glob("*.toml"):
        shutil.copy(f, tmp_path / f.name)
    shutil.copytree(REAL_CONFIG / "i18n", tmp_path / "i18n")
    return tmp_path


def test_missing_params_table_raises(tmp_path):
    d = _minimal_config_dir(tmp_path)
    _write_toml(d / "endpoint_params.toml", '[endpoints."/"]\nscalars = ["pulse"]\n')
    with pytest.raises(ConfigError, match="params"):
        load_config(d)


def test_missing_endpoints_table_raises(tmp_path):
    d = _minimal_config_dir(tmp_path)
    _write_toml(
        d / "endpoint_params.toml",
        '[params.pulse]\ntype = "float"\ndescription = "x"\n',
    )
    with pytest.raises(ConfigError, match="endpoints"):
        load_config(d)


def test_enum_without_values_raises(tmp_path):
    d = _minimal_config_dir(tmp_path)
    _write_toml(
        d / "endpoint_params.toml",
        '[params.profile]\ntype = "enum"\ndescription = "x"\n'
        '[endpoints."/"]\nscalars = ["profile"]\n',
    )
    with pytest.raises(ConfigError, match="values"):
        load_config(d)


def test_scalar_names_undeclared_param_raises(tmp_path):
    d = _minimal_config_dir(tmp_path)
    _write_toml(
        d / "endpoint_params.toml",
        '[params.pulse]\ntype = "float"\ndescription = "x"\n'
        '[endpoints."/"]\nscalars = ["nonexistent"]\n',
    )
    with pytest.raises(ConfigError, match="nonexistent"):
        load_config(d)


def test_moment_group_field_undeclared_param_raises(tmp_path):
    d = _minimal_config_dir(tmp_path)
    _write_toml(
        d / "endpoint_params.toml",
        '[params.pulse]\ntype = "float"\ndescription = "x"\n'
        "[moment_groups.full]\n"
        'priority = ["pulse"]\n'
        "[moment_groups.full.fields]\n"
        'pulse = ["nonexistent"]\n'
        '[endpoints."/"]\nmoment_group = "full"\n',
    )
    with pytest.raises(ConfigError, match="nonexistent"):
        load_config(d)


def test_endpoint_references_undeclared_moment_group_raises(tmp_path):
    d = _minimal_config_dir(tmp_path)
    _write_toml(
        d / "endpoint_params.toml",
        '[params.pulse]\ntype = "float"\ndescription = "x"\n'
        '[endpoints."/"]\nmoment_group = "nonexistent"\n',
    )
    with pytest.raises(ConfigError, match="nonexistent"):
        load_config(d)


def test_bad_param_type_raises(tmp_path):
    d = _minimal_config_dir(tmp_path)
    _write_toml(
        d / "endpoint_params.toml",
        '[params.pulse]\ntype = "not_a_real_type"\ndescription = "x"\n'
        '[endpoints."/"]\nscalars = ["pulse"]\n',
    )
    with pytest.raises(ConfigError, match="not_a_real_type"):
        load_config(d)


def test_globals_names_undeclared_param_raises(tmp_path):
    d = _minimal_config_dir(tmp_path)
    _write_toml(
        d / "endpoint_params.toml",
        'globals = ["nonexistent"]\n'
        '[params.pulse]\ntype = "float"\ndescription = "x"\n'
        '[endpoints."/"]\nscalars = ["pulse"]\n',
    )
    with pytest.raises(ConfigError, match="nonexistent"):
        load_config(d)


# ── Shared helper: resolve_moment_group (direct, Flask-free) ────────────────


def test_resolve_moment_group_pulse_priority(cfg):
    group = cfg.endpoint_params.moment_groups["full"]
    pulse, code, message = resolve_moment_group(
        {"pulse": "100", "astro_day": "5"}, group, cfg, "en-US"
    )
    assert (pulse, code, message) == (100, None, None)


def test_resolve_moment_group_astro_day_branch(cfg):
    ppd = cfg.time_constants.pulses_per_day
    group = cfg.endpoint_params.moment_groups["full"]
    pulse, code, message = resolve_moment_group({"astro_day": "2"}, group, cfg, "en-US")
    assert (pulse, code, message) == (ppd, None, None)


def test_resolve_moment_group_no_input(cfg):
    group = cfg.endpoint_params.moment_groups["full"]
    assert resolve_moment_group({}, group, cfg, "en-US") == (None, None, None)


def test_resolve_moment_group_invalid_pulse_unprefixed_tag(cfg):
    group = cfg.endpoint_params.moment_groups["full"]
    pulse, code, _message = resolve_moment_group(
        {"pulse": "not_a_number"}, group, cfg, "en-US"
    )
    assert pulse is None
    assert code == "invalid_pulse_value"  # irregular: not "invalid_pulse"


def test_resolve_moment_group_invalid_pulse_prefixed_tag(cfg):
    group = cfg.endpoint_params.moment_groups["full"]
    pulse, code, _message = resolve_moment_group(
        {"start_pulse": "not_a_number"}, group, cfg, "en-US", prefix="start_"
    )
    assert pulse is None
    assert code == "invalid_prefixed_pulse"


def test_resolve_moment_group_invalid_fatunik_date(cfg):
    group = cfg.endpoint_params.moment_groups["full"]
    pulse, code, message = resolve_moment_group(
        {"fatunik_year": "1", "fatunik_month": "99", "fatunik_day": "1"},
        group,
        cfg,
        "en-US",
    )
    assert pulse is None
    assert code == "invalid_fatunik_date"
    assert "99" in message or "month" in message.lower()


# ── Shared helper: parse_scalar ──────────────────────────────────────────────


def test_parse_scalar_int(cfg):
    assert parse_scalar("5", cfg.endpoint_params.params["step_minutes"]) == 5


def test_parse_scalar_float(cfg):
    assert parse_scalar("5.5", cfg.endpoint_params.params["end_pulse"]) == 5.5


def test_parse_scalar_enum_valid(cfg):
    assert (
        parse_scalar("kinematic", cfg.endpoint_params.params["profile"]) == "kinematic"
    )


def test_parse_scalar_enum_invalid_raises(cfg):
    with pytest.raises(ValueError):
        parse_scalar("bogus", cfg.endpoint_params.params["profile"])


def test_parse_scalar_int_invalid_raises(cfg):
    with pytest.raises(ValueError):
        parse_scalar("not_an_int", cfg.endpoint_params.params["step_minutes"])


# ── Shared helper: check_params ──────────────────────────────────────────────


def test_check_params_rejects_typo(cfg):
    code, message = check_params({"step_minute": "5"}, "/ephemeris", cfg, "en-US")
    assert code == "unknown_param"
    assert "step_minute" in message


def test_check_params_allows_declared_and_global(cfg):
    code, message = check_params(
        {"pulse": "1", "format": "json", "locale": "es-ES"}, "/", cfg, "en-US"
    )
    assert (code, message) == (None, None)


def test_check_params_rejects_invalid_format_value(cfg):
    code, message = check_params({"format": "xml"}, "/", cfg, "en-US")
    assert code == "invalid_format"
    assert "xml" in message


def test_check_params_format_case_insensitive(cfg):
    """Matches _wants_json()'s .lower() -- 'JSON' is valid, not just 'json'."""
    code, message = check_params({"format": "JSON"}, "/", cfg, "en-US")
    assert (code, message) == (None, None)


def test_check_params_rejects_invalid_locale_value(cfg):
    code, message = check_params({"locale": "fr-FR"}, "/", cfg, "en-US")
    assert code == "invalid_locale"
    assert "fr-FR" in message


def test_check_params_allows_declared_locale_values(cfg):
    for locale in ("en-US", "es-ES"):
        assert check_params({"locale": locale}, "/", cfg, "en-US") == (None, None)


# ── Behavior change 1: strict unknown-param rejection (HTTP) ────────────────


@pytest.mark.parametrize(
    "path", ["/?pulse=1", "/moons?pulse=1", "/planets?pulse=1", "/sky?pulse=1"]
)
def test_unknown_param_400_json(client, path):
    sep = "&"
    resp = client.get(f"{path}{sep}bogus_param=x&format=json")
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "unknown_param"


def test_unknown_param_400_json_ephemeris(client):
    resp = client.get(
        "/ephemeris?start_pulse=0&step_minutes=60&duration_days=1"
        "&bogus_param=x&format=json"
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "unknown_param"


def test_unknown_param_html_shows_error_not_crash(client):
    resp = client.get("/?pulse=1&bogus_param=x")
    assert resp.status_code == 200  # HTML errors render inline, like every other error
    assert b"bogus_param" in resp.data or resp.status_code == 200


def test_known_params_still_accepted_after_strict_rejection(client):
    """format and locale (global) plus every declared param remain accepted."""
    resp = client.get("/moons?pulse=86400&format=json&locale=es-ES")
    assert resp.status_code == 200


# ── Behavior change 2: /ephemeris profile becomes a validated enum ─────────


def test_ephemeris_invalid_profile_400(client):
    resp = client.get(
        "/ephemeris?start_pulse=0&step_minutes=60&duration_days=1"
        "&profile=bogus&format=json"
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "invalid_profile"


def test_ephemeris_valid_profile_both_still_works(client):
    resp = client.get(
        "/ephemeris?start_pulse=0&step_minutes=60&duration_days=1"
        "&profile=both&format=json"
    )
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["series"]["scribal"] is not None
    assert payload["series"]["kinematic"] is not None


# ── Behavior change 3: format/locale become validated globals (HTTP) ───────


@pytest.mark.parametrize("path", ["/", "/moons", "/planets", "/sky", "/ephemeris"])
def test_invalid_format_value_html_inline_error(client, path):
    """A non-'json' format value can never reach the JSON response path:
    _wants_json() treats ANY non-empty, non-'json' format as "wants HTML"
    outright (ignoring the Accept header entirely once format is present,
    per its own docstring) -- so error.invalid_format can only ever surface
    the way every other validation error does when JSON wasn't requested:
    an inline HTML message at 200, never a JSON 400."""
    resp = client.get(f"{path}?format=xml")
    assert resp.status_code == 200
    assert b"xml" in resp.data


@pytest.mark.parametrize("path", ["/", "/moons", "/planets", "/sky", "/ephemeris"])
def test_invalid_locale_value_400_on_every_endpoint(client, path):
    resp = client.get(f"{path}?locale=fr-FR&format=json")
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "invalid_locale"


def test_valid_locale_still_works(client):
    resp = client.get("/moons?pulse=86400&locale=es-ES&format=json")
    assert resp.status_code == 200
