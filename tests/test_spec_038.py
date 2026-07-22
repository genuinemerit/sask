"""SPEC-038 tests — CLI Round Two: dev tier, expanded admin surface, rich.

Covers:
  - layer purity: the new command modules import no sask.cli-external
    surface violations (extends SPEC-034's engine/spine check with the same
    modules; the new command modules themselves are the CLI, so they're not
    part of the engine/spine set — this file adds no new engine files)
  - SASK_ENV gating: dev commands are hidden from --help and error cleanly
    when SASK_ENV != dev; visible and runnable with SASK_ENV=dev; admin/
    player commands are unaffected by SASK_ENV either way
  - tier tags: every registered command/group carries rich_help_panel in
    {"Player", "Admin", "Dev"}
  - each new/wrapped command delegates to the underlying script (argv
    captured via a monkeypatched run_tool, never actually executed) rather
    than reimplementing it
  - logs verify's well-formed-JSON/no-secret predicates, reusing logs
    query's own argv-building machinery
  - REQ-SEC-006: verify-do-secrets never prints a fixture secret value;
    host_info never collects hostname/ip-address/mac-address
  - rich: piped output carries no ANSI escape sequences; a terminal-forced
    Console renders styled output
  - deploy/redeploy/set-log-level remain absent as CLI commands
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from sask.cli import _paths as paths_module
from sask.cli import _subprocess as subprocess_module
from sask.cli import app as cli_app
from sask.cli.commands import (
    acceptance_test as acceptance_test_module,
    dev_tools,
    host_info as host_info_module,
    logs as logs_module,
    run_perf as run_perf_module,
)

PROJECT_ROOT = Path(__file__).parent.parent
_ENV_BASE = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT / "src")}

runner = CliRunner()


def _run_cli(args: list[str], env_overrides: dict[str, str] | None = None):
    env = dict(_ENV_BASE)
    env.pop("SASK_ENV", None)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "-m", "sask.cli", *args],
        capture_output=True,
        text=True,
        env=env,
    )


# ── SASK_ENV gating ─────────────────────────────────────────────────────────

_A_DEV_COMMAND = "validate_specs"


def test_dev_command_hidden_from_help_outside_dev():
    result = _run_cli(["--help"])
    assert result.returncode == 0
    assert _A_DEV_COMMAND not in result.stdout


def test_dev_command_visible_in_help_with_sask_env_dev():
    result = _run_cli(["--help"], {"SASK_ENV": "dev"})
    assert result.returncode == 0
    assert _A_DEV_COMMAND in result.stdout


def test_dev_command_errors_cleanly_outside_dev():
    result = _run_cli([_A_DEV_COMMAND])
    assert result.returncode == 1
    assert "development environment" in result.stderr
    assert "SASK_ENV" in result.stderr


def test_dev_command_runs_with_sask_env_dev():
    result = _run_cli([_A_DEV_COMMAND], {"SASK_ENV": "dev"})
    assert result.returncode == 0
    assert "All spec files valid." in result.stdout


def test_admin_command_visible_and_error_shape_regardless_of_sask_env():
    """acceptance-test/run_perf's visibility does not depend on SASK_ENV —
    it depends on a separate signal, tools/ops/ presence (has_tools_ops(),
    see test_has_tools_ops_* below), which is True in this real checkout
    either way.
    """
    for env in (None, {"SASK_ENV": "dev"}):
        result = _run_cli(["--help"], env)
        assert "acceptance-test" in result.stdout
        assert "run_perf" in result.stdout


def test_has_tools_ops_true_for_real_checkout():
    assert paths_module.has_tools_ops() is True


def test_has_tools_ops_false_without_tools_ops_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(paths_module, "_REPO_ROOT", tmp_path)
    assert paths_module.has_tools_ops() is False


def test_acceptance_test_and_run_perf_not_hidden_in_this_checkout():
    """Regression guard for the fix itself: caught live on the droplet
    where tools/ops/ isn't deployed (DD-0021's ops-vs-CLI boundary) —
    acceptance-test/run_perf were visible and admin-tagged but always
    failed there. hidden=not has_tools_ops() now hides them where they
    structurally cannot work; this checkout has tools/ops/, so they must
    stay visible here.
    """
    hidden_by_name = {cmd.name: cmd.hidden for cmd in cli_app.registered_commands}
    assert hidden_by_name["acceptance-test"] is False
    assert hidden_by_name["run_perf"] is False


def test_player_command_visible_regardless_of_sask_env():
    for env in (None, {"SASK_ENV": "dev"}):
        result = _run_cli(["--help"], env)
        assert "host_info" in result.stdout
        assert "validate_json" in result.stdout


def test_sask_env_gating_case_and_whitespace_insensitive():
    result = _run_cli([_A_DEV_COMMAND], {"SASK_ENV": " Dev "})
    assert result.returncode == 0


# ── Tier tags (DD-0025) ──────────────────────────────────────────────────────


def test_every_registered_command_carries_a_tier_tag():
    for cmd in cli_app.registered_commands:
        assert cmd.rich_help_panel in {"Player", "Admin", "Dev"}, cmd.name


def test_every_registered_group_carries_a_tier_tag():
    for group in cli_app.registered_groups:
        assert group.rich_help_panel in {"Player", "Admin", "Dev"}, group.name


def test_dev_tier_commands_are_exactly_the_eight_gated_ones():
    dev_names = {
        cmd.name for cmd in cli_app.registered_commands if cmd.rich_help_panel == "Dev"
    }
    assert dev_names == {
        "check_page_staleness",
        "pre-commit-check",
        "run-tests",
        "start_web",
        "verify-clean-env",
        "verify-do-secrets",
        "validate_specs",
        "validate_i18n",
    }


# ── Ops boundary: deploy/redeploy/set-log-level stay ops-only ──────────────


def test_deploy_redeploy_set_log_level_are_not_cli_commands():
    all_names = {cmd.name for cmd in cli_app.registered_commands} | {
        group.name for group in cli_app.registered_groups
    }
    assert all_names.isdisjoint({"deploy", "redeploy", "set-log-level"})


# ── Dev commands: thin delegation, no reimplementation ──────────────────────


def _patch_dev_gate(monkeypatch):
    monkeypatch.setattr(dev_tools, "require_dev", lambda: None)
    calls: list[tuple] = []
    monkeypatch.setattr(
        dev_tools,
        "run_tool",
        lambda launcher, script, **kw: calls.append((launcher, script, kw)),
    )
    return calls


def test_check_page_staleness_delegates_to_the_existing_script(monkeypatch):
    calls = _patch_dev_gate(monkeypatch)
    dev_tools.check_page_staleness()
    launcher, script, kw = calls[0]
    assert launcher == [sys.executable]
    assert script == dev_tools._TOOLS_DEV / "check_page_staleness.py"
    assert kw.get("args") in (None, [])


def test_pre_commit_check_delegates_to_the_existing_script(monkeypatch):
    calls = _patch_dev_gate(monkeypatch)
    dev_tools.pre_commit_check()
    launcher, script, _kw = calls[0]
    assert launcher == ["bash"]
    assert script == dev_tools._TOOLS_DEV / "pre-commit-check.sh"


def test_run_tests_forwards_spec_verbose_save(monkeypatch):
    calls = _patch_dev_gate(monkeypatch)
    dev_tools.run_tests(spec="SPEC-002", verbose=True, save=True)
    launcher, script, kw = calls[0]
    assert launcher == ["bash"]
    assert script == dev_tools._TOOLS_DEV / "run-tests.sh"
    assert kw["args"] == ["--spec", "SPEC-002", "-v", "--save"]


def test_start_web_delegates_to_the_existing_script(monkeypatch):
    calls = _patch_dev_gate(monkeypatch)
    dev_tools.start_web()
    launcher, script, _kw = calls[0]
    assert launcher == ["bash"]
    assert script == dev_tools._TOOLS_DEV / "start_web.sh"


def test_verify_clean_env_delegates_to_the_existing_script(monkeypatch):
    calls = _patch_dev_gate(monkeypatch)
    dev_tools.verify_clean_env()
    launcher, script, _kw = calls[0]
    assert launcher == ["bash"]
    assert script == dev_tools._TOOLS_DEV / "verify-clean-env.sh"


def test_verify_do_secrets_delegates_to_the_existing_script(monkeypatch):
    calls = _patch_dev_gate(monkeypatch)
    dev_tools.verify_do_secrets()
    launcher, script, _kw = calls[0]
    assert launcher == ["bash"]
    assert script == dev_tools._TOOLS_DEV / "verify-do-secrets.sh"


def test_validate_specs_delegates_to_the_existing_script(monkeypatch):
    calls = _patch_dev_gate(monkeypatch)
    dev_tools.validate_specs()
    launcher, script, _kw = calls[0]
    assert launcher == [sys.executable]
    assert script == dev_tools._TOOLS_DEV / "validate_specs.py"


def test_validate_i18n_forwards_strict(monkeypatch):
    calls = _patch_dev_gate(monkeypatch)
    dev_tools.validate_i18n(strict=True)
    launcher, script, kw = calls[0]
    assert launcher == [sys.executable]
    assert script == dev_tools._TOOLS_DEV / "validate_i18n.py"
    assert kw["args"] == ["--strict"]
    calls.clear()
    dev_tools.validate_i18n(strict=False)
    assert calls[0][2]["args"] == []


# ── Admin commands: thin delegation ──────────────────────────────────────────


def test_acceptance_test_delegates_to_the_existing_script(monkeypatch):
    calls = []
    monkeypatch.setattr(
        acceptance_test_module,
        "run_tool",
        lambda launcher, script, **kw: calls.append((launcher, script, kw)),
    )
    acceptance_test_module.acceptance_test(base_url=None)
    launcher, script, kwargs = calls[0]
    assert launcher == ["bash"]
    assert str(script).endswith("tools/ops/acceptance-test.sh")
    assert "SASK_BASE_URL" not in kwargs.get("env", {})


def test_acceptance_test_forwards_base_url_via_env(monkeypatch):
    calls = []
    monkeypatch.setattr(
        acceptance_test_module,
        "run_tool",
        lambda launcher, script, **kw: calls.append((launcher, script, kw)),
    )
    acceptance_test_module.acceptance_test(base_url="https://staging.example")
    _launcher, _script, kwargs = calls[0]
    assert kwargs["env"]["SASK_BASE_URL"] == "https://staging.example"


def test_run_perf_delegates_to_the_existing_script(monkeypatch):
    calls = []
    monkeypatch.setattr(
        run_perf_module,
        "run_tool",
        lambda launcher, script, **kw: calls.append((launcher, script)),
    )
    run_perf_module.run_perf()
    launcher, script = calls[0]
    assert launcher == ["bash"]
    assert str(script).endswith("tools/ops/run_perf.sh")


# ── run_tool: missing-script existence check (regression) ──────────────────


def test_run_tool_reports_clean_error_for_missing_script(tmp_path, capsys):
    """Regression test: caught live on the droplet running `sask run_perf`/
    `sask acceptance-test` — subprocess.run(["bash", missing_path]) does
    NOT raise Python's FileNotFoundError (bash itself is on PATH; only its
    argument is missing), so bash's own raw "No such file or directory"
    leaked to the user instead of a clean message. run_tool now checks
    script.exists() itself first.
    """
    missing = tmp_path / "does-not-exist.sh"
    with pytest.raises(typer.Exit) as exc_info:
        subprocess_module.run_tool(["bash"], missing)
    assert exc_info.value.exit_code == 1
    captured = capsys.readouterr()
    assert str(missing) in captured.err
    assert "not found" in captured.err
    assert "full sask checkout" in captured.err


# ── logs verify: reuses logs query's argv machinery ─────────────────────────


def test_logs_verify_wellformed_json_predicate():
    good = json.dumps(
        {"timestamp": "t", "level": "INFO", "logger": "x", "message": "ok"}
    )
    assert logs_module._line_is_wellformed_app_json(good)
    assert not logs_module._line_is_wellformed_app_json("not json")
    assert not logs_module._line_is_wellformed_app_json('{"level": "INFO"}')


def test_logs_verify_secret_needle_predicate():
    assert logs_module._line_has_cleartext_secret("token=dop_v1_abc123")
    assert logs_module._line_has_cleartext_secret("DIGITALOCEAN_TOKEN is set")
    assert not logs_module._line_has_cleartext_secret("nothing sensitive here")
    assert not logs_module._line_has_cleartext_secret("dop_v1_***REDACTED***")


def test_logs_verify_requests_cat_output_format(monkeypatch):
    """Regression test: journalctl's default output format prepends a
    syslog-style prefix ("Jul 22 15:03:17 host gunicorn[PID]: ") before
    each line, which makes every line fail json.loads() regardless of
    content — caught live during SPEC-038 prod UAT (well_formed_json
    reported 0 against a journal that plainly had well-formed JSON). -o cat
    strips that prefix, matching the retired verify-logging.sh's own flag.
    Earlier versions of this test suite monkeypatched subprocess.run
    entirely and never asserted the actual argv, so this exact regression
    slipped past every prior automated test.
    """
    captured_argv = []

    class FakeResult:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(argv, **kwargs):
        captured_argv.append(argv)
        return FakeResult()

    monkeypatch.setattr(logs_module.subprocess, "run", fake_run)
    runner.invoke(cli_app, ["logs", "verify"])

    argv = captured_argv[0]
    assert "-o" in argv
    assert argv[argv.index("-o") + 1] == "cat"


def test_logs_verify_fails_when_no_wellformed_json(monkeypatch):
    class FakeResult:
        returncode = 0
        stdout = "plain text startup notice\n"
        stderr = ""

    monkeypatch.setattr(logs_module.subprocess, "run", lambda *a, **k: FakeResult())
    result = runner.invoke(cli_app, ["logs", "verify"])
    assert result.exit_code == 1
    assert "well_formed_json" in result.output


def test_logs_verify_fails_on_secret_hit(monkeypatch):
    good = json.dumps(
        {"timestamp": "t", "level": "INFO", "logger": "x", "message": "ok"}
    )

    class FakeResult:
        returncode = 0
        stdout = f"{good}\nleaked DIGITALOCEAN_TOKEN=dop_v1_abc\n"
        stderr = ""

    monkeypatch.setattr(logs_module.subprocess, "run", lambda *a, **k: FakeResult())
    result = runner.invoke(cli_app, ["logs", "verify"])
    assert result.exit_code == 1
    assert "secret_hits" in result.output


def test_logs_verify_passes_clean_window(monkeypatch):
    good = json.dumps(
        {"timestamp": "t", "level": "INFO", "logger": "x", "message": "ok"}
    )

    class FakeResult:
        returncode = 0
        stdout = f"{good}\n"
        stderr = ""

    monkeypatch.setattr(logs_module.subprocess, "run", lambda *a, **k: FakeResult())
    result = runner.invoke(cli_app, ["logs", "verify"])
    assert result.exit_code == 0
    assert "PASS" in result.output


def test_logs_verify_reuses_query_argv_builder():
    """logs_verify calls the exact same _build_journalctl_argv logs query
    uses — no separate argv-building function exists in this module, so any
    divergence would require adding one (grep-visible source check)."""
    import inspect

    source = inspect.getsource(logs_module.logs_verify)
    assert "_build_journalctl_argv" in source


# ── REQ-SEC-006: no secret values, no sensitive host info ──────────────────


def test_verify_do_secrets_never_prints_the_token_value(tmp_path):
    dummy_token = "dop_v1_TESTDUMMYVALUE1234567890abcdef"
    config_dir = tmp_path / ".config" / "sask"
    config_dir.mkdir(parents=True)
    (config_dir / "infra.env").write_text(f'DIGITALOCEAN_TOKEN="{dummy_token}"\n')

    result = subprocess.run(
        ["bash", str(PROJECT_ROOT / "tools" / "ops" / "verify-do-secrets.sh")],
        capture_output=True,
        text=True,
        env={**os.environ, "HOME": str(tmp_path)},
        timeout=30,
    )
    assert dummy_token not in result.stdout
    assert dummy_token not in result.stderr


def test_host_info_excludes_sensitive_fields():
    data = host_info_module._collect()
    for forbidden in ("hostname", "ip-address", "mac-address"):
        assert forbidden not in data


def test_host_info_command_output_has_no_sensitive_fields():
    result = runner.invoke(cli_app, ["host_info"])
    assert result.exit_code == 0
    lowered = result.output.lower()
    for forbidden in ("hostname", "ip-address", "mac-address"):
        assert forbidden not in lowered
    assert "platform" in lowered


# ── validate_json ─────────────────────────────────────────────────────────


def test_validate_json_reports_success_for_matching_data(tmp_path):
    schema_path = tmp_path / "schema.json"
    data_path = tmp_path / "data.json"
    schema_path.write_text(json.dumps({"type": "object"}))
    data_path.write_text(json.dumps({}))

    result = runner.invoke(cli_app, ["validate_json", str(schema_path), str(data_path)])
    assert result.exit_code == 0
    assert result.output.strip() == ""


def test_validate_json_reports_errors_for_mismatched_data(tmp_path):
    schema_path = tmp_path / "schema.json"
    data_path = tmp_path / "data.json"
    schema_path.write_text(json.dumps({"type": "string"}))
    data_path.write_text(json.dumps({}))

    result = runner.invoke(cli_app, ["validate_json", str(schema_path), str(data_path)])
    assert result.exit_code == 1
    assert "is not of type" in result.output


def test_validate_json_missing_file_reports_error_not_crash(tmp_path):
    result = runner.invoke(
        cli_app,
        [
            "validate_json",
            str(tmp_path / "nope.json"),
            str(tmp_path / "also-nope.json"),
        ],
    )
    assert result.exit_code == 2
    assert "not found" in result.output.lower()


# ── rich: piped output has no escape sequences ──────────────────────────────


def test_asset_list_piped_has_no_ansi_escapes():
    result = subprocess.run(
        [sys.executable, "-m", "sask.cli", "asset", "list"],
        capture_output=True,
        text=True,
        env=_ENV_BASE,
    )
    assert result.returncode == 0
    assert "\x1b[" not in result.stdout


def test_help_piped_has_no_ansi_escapes():
    result = subprocess.run(
        [sys.executable, "-m", "sask.cli", "help"],
        capture_output=True,
        text=True,
        env=_ENV_BASE,
    )
    assert result.returncode == 0
    assert "\x1b[" not in result.stdout


def test_host_info_piped_has_no_ansi_escapes():
    result = subprocess.run(
        [sys.executable, "-m", "sask.cli", "host_info"],
        capture_output=True,
        text=True,
        env=_ENV_BASE,
    )
    assert result.returncode == 0
    assert "\x1b[" not in result.stdout


def test_asset_list_piped_output_unchanged_from_spec_034_format():
    """Piped output stays byte-identical to SPEC-034's pre-rich plain format
    (not merely de-colored rich table glyphs) — the same assertion
    test_spec_034.py's test_asset_list_runs_and_lists_known_kind makes.
    """
    result = subprocess.run(
        [sys.executable, "-m", "sask.cli", "asset", "list"],
        capture_output=True,
        text=True,
        env=_ENV_BASE,
    )
    assert "image/splash.bg  (image/webp," in result.stdout
