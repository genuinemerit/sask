"""SPEC-035 tests — i18n machinery, dual-mechanism canary, validator, locale selection.

Covers:
  - resolve()'s fallback chain (locale hit; base fallback; raw-tag
    fallback; never raises) and layer purity (no Flask/engine/cli imports)
  - one message unit (SeasonInfo) rendering differently per bound locale
    on both web and CLI, with season_id itself unchanged across locales
  - parallel-doc selection with base fallback, and REQ-SEC-005 path safety
  - the three-severity validator (tools/dev/validate_i18n.py) in
    permissive and strict mode
  - locale selection: web cookie + Accept-Language default + toggle
    override; CLI flag + env var + flag-overrides-env-var precedence
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sask.config_loader import I18nCatalog, load_config
from sask.help.loader import discover_parallel_docs
from sask.i18n.catalog import best_locale, resolve
from sask.i18n.tags import season_tag
from sask.web import create_app

PROJECT_ROOT = Path(__file__).parent.parent
REAL_CONFIG = PROJECT_ROOT / "config"
REAL_HELP_DIR = PROJECT_ROOT / "docs" / "help"

sys.path.insert(0, str(PROJECT_ROOT / "tools" / "dev"))
import validate_i18n  # noqa: E402

runner = CliRunner()


def _catalog(entries: dict[str, dict[str, str]], base: str = "en-US") -> I18nCatalog:
    return I18nCatalog(
        base_locale=base, locales=tuple(sorted(entries)), entries=entries
    )


# ── Fallback chain ──────────────────────────────────────────────────────────


def test_season_tag_maps_domain_identifier_to_tag():
    assert season_tag("greening") == "season.greening"


def test_resolve_hits_locale_catalog():
    cat = _catalog({"en-US": {"a": "A"}, "es-ES": {"a": "Ay"}})
    assert resolve("a", "es-ES", cat) == "Ay"


def test_resolve_falls_back_to_base_locale():
    cat = _catalog({"en-US": {"a": "A"}, "es-ES": {}})
    assert resolve("a", "es-ES", cat) == "A"


def test_resolve_falls_back_to_raw_tag_when_absent_from_base_too():
    cat = _catalog({"en-US": {}, "es-ES": {}})
    assert resolve("nav.missing", "es-ES", cat) == "nav.missing"


def test_resolve_never_raises_on_any_miss():
    cat = _catalog({"en-US": {}})
    # Unknown locale entirely, unknown tag -- still no exception.
    assert resolve("x.y", "fr-FR", cat) == "x.y"


def test_resolve_distinguishes_empty_string_from_absent():
    """The legacy `fallback or i18n_id` bug, deliberately not repeated:
    an intentionally-empty catalog value must not be treated as a miss.
    """
    cat = _catalog({"en-US": {"a": ""}})
    assert resolve("a", "en-US", cat) == ""


# ── One unit, many locales, many adapters ──────────────────────────────────


def test_season_name_renders_en_us_on_web():
    app = create_app(config_dir=REAL_CONFIG)
    client = app.test_client()
    resp = client.get("/sky?pulse=0")
    assert resp.status_code == 200
    assert b"Greening" in resp.data


def test_season_name_renders_es_es_on_web():
    app = create_app(config_dir=REAL_CONFIG)
    client = app.test_client()
    client.set_cookie("locale", "es-ES")
    resp = client.get("/sky?pulse=0")
    assert resp.status_code == 200
    assert "Reverdecer".encode() in resp.data


def test_season_name_renders_en_us_on_cli():
    result = runner.invoke(_cli_app(), ["season", "--pulse", "0"])
    assert result.exit_code == 0
    assert "Greening" in result.output


def test_season_name_renders_es_es_on_cli():
    result = runner.invoke(_cli_app(), ["--lang", "es-ES", "season", "--pulse", "0"])
    assert result.exit_code == 0
    assert "Reverdecer" in result.output


def test_season_id_unchanged_across_locales():
    result_en = runner.invoke(_cli_app(), ["season", "--pulse", "0"])
    result_es = runner.invoke(_cli_app(), ["--lang", "es-ES", "season", "--pulse", "0"])
    assert "season_id      : greening" in result_en.output
    assert "season_id      : greening" in result_es.output


def _cli_app():
    from sask.cli import app as cli_app

    return cli_app


# ── Parallel documents ──────────────────────────────────────────────────────


def test_parallel_doc_selected_for_declared_locale():
    docs = discover_parallel_docs(REAL_HELP_DIR)
    assert ("getting-started", "es-ES") in docs
    text = docs[("getting-started", "es-ES")].read_text(encoding="utf-8")
    assert "Primeros pasos" in text


def test_parallel_doc_falls_back_to_base_when_locale_doc_absent():
    app = create_app(config_dir=REAL_CONFIG)
    client = app.test_client()
    client.set_cookie("locale", "es-ES")
    # calendar-lore has no es-ES parallel doc -- must serve the base (English)
    resp = client.get("/help/calendar-lore")
    assert resp.status_code == 200
    assert b"Calendar lore" in resp.data


def test_parallel_doc_selection_rejects_traversal_locale_value():
    """REQ-SEC-005: a crafted locale value must resolve via dict membership
    only, never a filesystem read outside the known (topic, locale) set.
    """
    docs = discover_parallel_docs(REAL_HELP_DIR)
    traversal = "../../../../etc/passwd"
    assert docs.get(("getting-started", traversal)) is None
    # The known set itself contains no path-escaping keys or values.
    for (topic, locale), path in docs.items():
        assert ".." not in topic
        assert ".." not in locale
        assert path.is_relative_to(REAL_HELP_DIR.resolve())


# ── Validator ────────────────────────────────────────────────────────────────


def test_validator_flags_malformed_tag_as_hard_error(tmp_path):
    (tmp_path / "en-US.toml").write_text('[tags]\n"Bad Tag" = "x"\n')
    messages = validate_i18n.run(tmp_path, strict=False)
    assert any("malformed tag" in m and m.startswith("ERROR") for m in messages)


def test_validator_flags_missing_base_as_hard_error(tmp_path):
    (tmp_path / "en-US.toml").write_text('[tags]\n"nav.a" = "A"\n')
    (tmp_path / "es-ES.toml").write_text('[tags]\n"nav.a" = "A"\n"nav.orphan" = "y"\n')
    messages = validate_i18n.run(tmp_path, strict=False)
    assert any(
        "missing content for tag 'nav.orphan'" in m and m.startswith("ERROR")
        for m in messages
    )


def test_validator_warns_on_missing_non_base_in_permissive_mode(tmp_path):
    (tmp_path / "en-US.toml").write_text('[tags]\n"nav.a" = "A"\n"nav.b" = "B"\n')
    (tmp_path / "es-ES.toml").write_text('[tags]\n"nav.a" = "A"\n')
    messages = validate_i18n.run(tmp_path, strict=False)
    assert any(m.startswith("WARNING") and "nav.b" in m for m in messages)
    assert not any(m.startswith("ERROR") for m in messages)


def test_validator_hard_fails_on_missing_non_base_in_strict_mode(tmp_path):
    (tmp_path / "en-US.toml").write_text('[tags]\n"nav.a" = "A"\n"nav.b" = "B"\n')
    (tmp_path / "es-ES.toml").write_text('[tags]\n"nav.a" = "A"\n')
    messages = validate_i18n.run(tmp_path, strict=True)
    assert any(m.startswith("ERROR") and "nav.b" in m for m in messages)


def test_validator_clean_catalog_passes_both_modes(tmp_path):
    (tmp_path / "en-US.toml").write_text('[tags]\n"nav.a" = "A"\n')
    (tmp_path / "es-ES.toml").write_text('[tags]\n"nav.a" = "Ay"\n')
    assert validate_i18n.run(tmp_path, strict=False) == []
    assert validate_i18n.run(tmp_path, strict=True) == []


def test_real_catalog_passes_strict_validation():
    """The actual committed config/i18n/*.toml must be fully complete --
    the canary itself must not fail the deploy gate it introduces.
    """
    messages = validate_i18n.run(PROJECT_ROOT / "config" / "i18n", strict=True)
    assert messages == []


# ── Locale selection ─────────────────────────────────────────────────────────


def test_web_locale_defaults_from_accept_language():
    cfg = load_config(REAL_CONFIG)
    locale = best_locale(None, "es-ES,es;q=0.9,en;q=0.8", cfg.i18n)
    assert locale == "es-ES"


def test_web_toggle_overrides_accept_language():
    app = create_app(config_dir=REAL_CONFIG)
    client = app.test_client()
    client.set_cookie("locale", "es-ES")
    resp = client.get("/?locale=en-US", headers={"Accept-Language": "es-ES,es;q=0.9"})
    assert resp.status_code == 200
    assert b'lang="en-US"' in resp.data


def test_web_toggle_persists_via_cookie():
    app = create_app(config_dir=REAL_CONFIG)
    client = app.test_client()
    resp = client.get("/?locale=es-ES")
    set_cookie = resp.headers.get("Set-Cookie", "")
    assert "locale=es-ES" in set_cookie


def test_cli_locale_defaults_to_base():
    result = runner.invoke(_cli_app(), ["season", "--pulse", "0"])
    assert "locale         : en-US" in result.output


def test_cli_lang_flag_overrides_default():
    result = runner.invoke(_cli_app(), ["--lang", "es-ES", "season", "--pulse", "0"])
    assert "locale         : es-ES" in result.output


def test_cli_sask_locale_env_var_sets_default():
    result = subprocess.run(
        [sys.executable, "-m", "sask.cli", "season", "--pulse", "0"],
        capture_output=True,
        text=True,
        env={
            **__import__("os").environ,
            "PYTHONPATH": str(PROJECT_ROOT / "src"),
            "SASK_LOCALE": "es-ES",
        },
    )
    assert "locale         : es-ES" in result.stdout


def test_cli_flag_overrides_env_var():
    result = subprocess.run(
        [sys.executable, "-m", "sask.cli", "--lang", "en-US", "season", "--pulse", "0"],
        capture_output=True,
        text=True,
        env={
            **__import__("os").environ,
            "PYTHONPATH": str(PROJECT_ROOT / "src"),
            "SASK_LOCALE": "es-ES",
        },
    )
    assert "locale         : en-US" in result.stdout


# ── Layer purity: sask/i18n/catalog.py imports no Flask/engine/cli ─────────

_I18N_FILES = [PROJECT_ROOT / "src" / "sask" / "i18n" / "catalog.py"]


def _forbidden_imports_in(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                lowered = alias.name.lower()
                if (
                    "flask" in lowered
                    or lowered.startswith("sask.calendar")
                    or lowered.startswith("sask.cli")
                    or lowered.startswith("sask.web")
                ):
                    found.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").lower()
            if (
                "flask" in module
                or module.startswith("sask.calendar")
                or module.startswith("sask.cli")
                or module.startswith("sask.web")
            ):
                found.append(f"from {module} import ...")
    return found


@pytest.mark.parametrize("path", _I18N_FILES, ids=lambda p: p.name)
def test_i18n_module_has_no_flask_engine_or_cli_import(path: Path):
    assert _forbidden_imports_in(path) == []
