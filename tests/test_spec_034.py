"""SPEC-034 tests — CLI: Typer consumer adapter, initial commands, clean-room purity.

Covers:
  - layer purity: engine/spine modules (config_loader.py, logsetup.py,
    message.py, calendar/*.py, asset/*.py) import no sask.cli (AST check,
    mirroring test_spec_005.py / test_spec_032.py's Flask-free engine check)
  - help renders the same Markdown source discover_topics()/index_path()
    resolve for the web adapter; unknown topic reports an error, no crash
  - convert delegates to sask.calendar.pulse.pulse_info() and prints the
    same field values that function returns for the same pulse
  - asset list / asset info never have access to fetch_payload (descriptor-
    only, structurally — the module never imports it)
  - config check reports success with counts for a valid config, and a
    clean error (no traceback) for an invalid one
  - logs query's journalctl argv-building is tested directly, without a
    live journal, including safe handling of a shell-metacharacter-laden
    --grep value
  - the CLI app is runnable via typer.testing.CliRunner
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sask.calendar import pulse as pulse_module
from sask.cli import app as cli_app
from sask.cli.commands import asset as asset_module
from sask.cli.commands import calendar as calendar_module
from sask.cli.commands import config as config_module
from sask.cli.commands import help as help_module
from sask.cli.commands import logs as logs_module
from sask.cli._config import resolve_and_load_config
from sask.config_loader import load_config
from sask.help.loader import discover_topics, index_path

PROJECT_ROOT = Path(__file__).parent.parent
REAL_CONFIG = PROJECT_ROOT / "config"
REAL_HELP_DIR = PROJECT_ROOT / "docs" / "help"

runner = CliRunner()


# ── Layer purity: engine/spine imports no sask.cli ────────────────────────────

_ENGINE_FILES = (
    [
        PROJECT_ROOT / "src" / "sask" / "config_loader.py",
        PROJECT_ROOT / "src" / "sask" / "logsetup.py",
        PROJECT_ROOT / "src" / "sask" / "message.py",
    ]
    + sorted((PROJECT_ROOT / "src" / "sask" / "calendar").glob("*.py"))
    + sorted((PROJECT_ROOT / "src" / "sask" / "asset").glob("*.py"))
)


def _cli_imports_in(path: Path) -> list[str]:
    """Return sask.cli import lines found in path (SPEC-034)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.lower().startswith("sask.cli"):
                    found.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").lower()
            if module.startswith("sask.cli"):
                found.append(f"from {module} import ...")
    return found


@pytest.mark.parametrize("path", _ENGINE_FILES, ids=lambda p: p.name)
def test_engine_modules_import_no_cli(path: Path):
    assert _cli_imports_in(path) == []


# ── help ────────────────────────────────────────────────────────────────────


def test_help_index_renders_same_markdown_source_as_web():
    web_index = index_path(REAL_HELP_DIR)
    assert web_index is not None
    expected_text = web_index.read_text(encoding="utf-8")

    result = runner.invoke(cli_app, ["help"])
    assert result.exit_code == 0
    assert expected_text in result.output


def test_help_topic_renders_same_markdown_source_as_web():
    topics = discover_topics(REAL_HELP_DIR)
    topic_name, topic_path = next(iter(sorted(topics.items())))
    expected_text = topic_path.read_text(encoding="utf-8")

    result = runner.invoke(cli_app, ["help", topic_name])
    assert result.exit_code == 0
    assert expected_text in result.output


def test_help_unknown_topic_reports_error_not_crash():
    result = runner.invoke(cli_app, ["help", "no-such-topic"])
    assert result.exit_code == 1
    assert result.exception is None or isinstance(result.exception, SystemExit)


# ── convert ───────────────────────────────────────────────────────────────


def test_convert_delegates_to_pulse_info(monkeypatch):
    calls = []
    original = calendar_module.pulse_info

    def spy(pulse, cfg):
        calls.append(pulse)
        return original(pulse, cfg)

    monkeypatch.setattr(calendar_module, "pulse_info", spy)
    calendar_module.convert(pulse=777)

    assert calls == [777]


def test_convert_prints_same_fields_pulse_info_returns():
    cfg = load_config(REAL_CONFIG)
    expected = pulse_module.pulse_info(0, cfg)

    result = runner.invoke(cli_app, ["convert", "--pulse", "0"])
    assert result.exit_code == 0
    assert f"pulse           : {expected.pulse}" in result.output
    assert f"astro_day       : {expected.astro_day}" in result.output
    assert f"day_pulse_offset: {expected.day_pulse_offset}" in result.output
    assert f"orbital_position: {expected.orbital_position}" in result.output


# ── asset ─────────────────────────────────────────────────────────────────


def test_asset_commands_have_no_access_to_fetch_payload():
    """Descriptor-only, structurally: the module never imports fetch_payload,
    so neither `asset list` nor `asset info` can read a payload file even
    by accident.
    """
    assert not hasattr(asset_module, "fetch_payload")


def test_asset_list_runs_and_lists_known_kind():
    result = runner.invoke(cli_app, ["asset", "list"])
    assert result.exit_code == 0
    assert "image/splash.bg" in result.output


def test_asset_info_known_asset():
    result = runner.invoke(cli_app, ["asset", "info", "image", "splash.bg"])
    assert result.exit_code == 0
    assert "content_type" in result.output


def test_asset_info_unknown_reports_not_found_not_crash():
    result = runner.invoke(cli_app, ["asset", "info", "image", "does-not-exist"])
    assert result.exit_code == 1
    assert "no such asset" in result.output


# ── config check ────────────────────────────────────────────────────────────


def test_config_check_reports_ok_for_valid_config():
    result = runner.invoke(
        cli_app, ["config", "check", "--config-dir", str(REAL_CONFIG)]
    )
    assert result.exit_code == 0
    assert "Config OK" in result.output
    assert "bodies" in result.output


def test_config_check_reports_error_for_invalid_config(tmp_path):
    result = runner.invoke(cli_app, ["config", "check", "--config-dir", str(tmp_path)])
    assert result.exit_code == 1
    assert "invalid" in result.output.lower()


# ── logs query: argv mapping, no live journal required ────────────────────


def test_logs_query_argv_maps_level_since_grep():
    argv = logs_module._build_journalctl_argv(
        unit="sask", user_scope=False, since="1 hour ago", grep="ERROR", lines=50
    )
    assert argv == [
        "journalctl",
        "-u",
        "sask",
        "--no-pager",
        "-n",
        "50",
        "--since",
        "1 hour ago",
        "--grep",
        "ERROR",
    ]


def test_logs_query_argv_uses_user_flag_for_dev_scope():
    argv = logs_module._build_journalctl_argv(
        unit="sask-dev", user_scope=True, since=None, grep=None, lines=100
    )
    assert argv[0] == "journalctl"
    assert "--user" in argv
    assert argv.index("--user") < argv.index("-u")
    assert "sask-dev" in argv


def test_logs_query_grep_value_is_single_argv_element_not_shell_interpolated():
    malicious = "; rm -rf / #"
    argv = logs_module._build_journalctl_argv(
        unit="sask", user_scope=False, since=None, grep=malicious, lines=10
    )
    # The value appears as exactly one literal argv element, never split or
    # concatenated into a shell string.
    assert malicious in argv
    assert argv.count(malicious) == 1
    joined = " ".join(argv)
    # Sanity: it's present as a substring of the joined form too (since
    # subprocess.run is called with this list and shell=False, the joined
    # form is never actually executed by a shell — this just confirms the
    # value wasn't mangled or dropped).
    assert malicious in joined


def test_line_matches_level_only_matches_wellformed_json():
    assert logs_module._line_matches_level(
        '{"level": "ERROR", "message": "x"}', "ERROR"
    )
    assert not logs_module._line_matches_level(
        '{"level": "INFO", "message": "x"}', "ERROR"
    )
    # gunicorn's own plain-text lines never match a level filter
    assert not logs_module._line_matches_level(
        "[2026-07-09 10:41:28 +0000] [4773] [INFO] Starting gunicorn", "INFO"
    )


# ── CLI runnable ──────────────────────────────────────────────────────────


def test_runnable_via_python_dash_m():
    """python -m sask.cli must work standalone via plain module import, not
    just the pyproject.toml console script — the console script only exists
    where sask itself is pip/poetry-installed with entry points (true in
    dev), but the droplet's app role installs only requirements.txt's
    dependencies and runs the app via PYTHONPATH (matching wsgi.py), never
    pip-installing the sask package itself. Caught live during SPEC-034's
    droplet UAT: `sask --help` on the droplet failed with "No such file or
    directory" for exactly this reason.
    """
    result = subprocess.run(
        [sys.executable, "-m", "sask.cli", "--help"],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT / "src")},
    )
    assert result.returncode == 0
    assert "convert" in result.stdout


def test_cli_logs_go_to_stderr_not_stdout():
    """Diagnostics (e.g. config_loader's "config loaded", emitted on every
    command that touches config) must not pollute stdout — noticed live
    during Dave's own droplet UAT: the log record was interleaving with
    actual command output, breaking any attempt to pipe/redirect results
    cleanly. main() configures logging to stderr specifically so stdout
    stays clean regardless.
    """
    result = subprocess.run(
        [sys.executable, "-m", "sask.cli", "convert", "--pulse", "0"],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT / "src")},
    )
    assert result.returncode == 0
    assert "config loaded" not in result.stdout
    assert "config loaded" in result.stderr
    assert "orbital_position" in result.stdout


def test_cli_app_is_runnable_via_typer_testrunner():
    result = runner.invoke(cli_app, ["--help"])
    assert result.exit_code == 0
    assert "convert" in result.output
    assert "asset" in result.output


def test_no_command_offers_a_service_mutating_action():
    """No SPEC-034 command name suggests service mutation (start/stop/restart/
    deploy/set-*) — a structural sanity check on the initial command set.
    """
    result = runner.invoke(cli_app, ["--help"])
    assert result.exit_code == 0
    forbidden = ("start", "stop", "restart", "deploy", "destroy", "set-log-level")
    lowered = result.output.lower()
    for word in forbidden:
        assert word not in lowered


# sanity: resolve_and_load_config's default path resolution actually finds
# the real project config (proves cli/_paths.py's walk-up depth is correct)
def test_resolve_and_load_config_default_finds_real_config():
    cfg = resolve_and_load_config()
    assert len(cfg.bodies) == 15


def test_config_module_and_help_module_importable():
    # Trivial import-shape guard: both modules expose the expected Typer app
    # / command callables used by cli/__init__.py's registration.
    assert config_module.app is not None
    assert callable(help_module.help_command)
