"""Typer CLI consumer adapter for sask (DD-0021, REQ-FUN-014, SPEC-034,
DD-0025, REQ-FUN-017, SPEC-038).

Thin adapter: each command parses args, calls the same clean-room
engine/spine functions the web adapter calls, and formats output. No domain
logic lives here or in commands/*.py — see
design/analysis/saskan-app-alt-port/legacy-cli-deepening.md for the legacy
anti-pattern this deliberately avoids.

cli/ may import the engine/spine (to call it); the engine/spine must never
import cli/ (layer-purity test, tests/test_spec_034.py).

Tier tagging (DD-0025): every command/group below is registered with
rich_help_panel="Player"/"Admin"/"Dev" — doubling as visible grouping in
--help and a structural tag tests can assert on
(app.registered_commands/registered_groups), the auth seam DD-0021 named.
Dev-tier commands are additionally hidden=not _IS_DEV, the one tier
DD-0025 enforces now (player/admin stay tagged-but-unenforced until auth
exists) — SASK_ENV is read once here, the same fresh-process-per-invocation
model SASK_LOG_LEVEL/SASK_LOCALE already use.
"""

from __future__ import annotations

import sys

import typer

from sask import logsetup
from sask.cli._env import is_dev_env
from sask.cli.commands import (
    acceptance_test,
    asset,
    calendar,
    config,
    dev_tools,
    help as help_cmd,
    host_info,
    logs,
    run_perf,
    season,
    validate_json,
)

app = typer.Typer(help="sask calendar-engine CLI", no_args_is_help=True)

_IS_DEV = is_dev_env()


@app.callback()
def _root(
    ctx: typer.Context,
    lang: str = typer.Option(
        None,
        "--lang",
        envvar="SASK_LOCALE",
        help="Locale for interface text/results, e.g. es-ES (DD-0022). "
        "Flag overrides SASK_LOCALE overrides the catalog's base locale.",
    ),
) -> None:
    """sask — Saskan calendar engine CLI."""
    # Required no-op-shaped root callback: the legacy CLI's own devlog
    # records a real bug (a subcommand silently broke) when a root
    # callback was omitted entirely. Kept deliberately, not rediscovered —
    # see legacy-cli-deepening.md. ctx.obj threads the resolved --lang/
    # SASK_LOCALE value to subcommands that need it (season) — Typer's
    # envvar= handles flag-overrides-env-var-overrides-default precedence
    # natively, no hand-rolled logic needed.
    ctx.obj = {"lang": lang}


# Player tier — read-only, safe, eventually guest/registered (tagged now,
# enforced by auth later).
app.command("help", rich_help_panel="Player")(help_cmd.help_command)
app.command("convert", rich_help_panel="Player")(calendar.convert)
app.command("season", rich_help_panel="Player")(season.season)
app.command("host_info", rich_help_panel="Player")(host_info.host_info)
app.command("validate_json", rich_help_panel="Player")(validate_json.validate_json)
app.add_typer(asset.app, name="asset", rich_help_panel="Player")

# Admin tier — owner diagnostics/verification that consume the app; no
# service mutation (tagged now, enforced by auth later).
app.add_typer(config.app, name="config", rich_help_panel="Admin")
app.add_typer(logs.app, name="logs", rich_help_panel="Admin")
app.command("acceptance-test", rich_help_panel="Admin")(acceptance_test.acceptance_test)
app.command("run_perf", rich_help_panel="Admin")(run_perf.run_perf)

# Dev tier — development/build/verification tooling, only meaningful in a
# development environment. Enforced NOW via SASK_ENV (not auth): hidden from
# --help outside dev, and each command body also refuses to run outside dev
# (cli/_env.py::require_dev) as defense in depth.
_dev_hidden = not _IS_DEV
app.command("check_page_staleness", hidden=_dev_hidden, rich_help_panel="Dev")(
    dev_tools.check_page_staleness
)
app.command("pre-commit-check", hidden=_dev_hidden, rich_help_panel="Dev")(
    dev_tools.pre_commit_check
)
app.command("run-tests", hidden=_dev_hidden, rich_help_panel="Dev")(dev_tools.run_tests)
app.command("start_web", hidden=_dev_hidden, rich_help_panel="Dev")(dev_tools.start_web)
app.command("verify-clean-env", hidden=_dev_hidden, rich_help_panel="Dev")(
    dev_tools.verify_clean_env
)
app.command("verify-do-secrets", hidden=_dev_hidden, rich_help_panel="Dev")(
    dev_tools.verify_do_secrets
)
app.command("validate_specs", hidden=_dev_hidden, rich_help_panel="Dev")(
    dev_tools.validate_specs
)
app.command("validate_i18n", hidden=_dev_hidden, rich_help_panel="Dev")(
    dev_tools.validate_i18n
)


def main() -> None:
    """Console-script entry point (pyproject.toml: sask = "sask.cli:main").

    Calls logsetup.configure() once, at invocation time — never at import
    time (SPEC-032 named the legacy project's import-time configure() call
    an anti-pattern; this CLI does not repeat it). Logs to stderr, not the
    stdout default create_app() uses: the web app's stdout is captured by
    journald, invisible in normal use, but the CLI is a fresh process per
    invocation run directly at a terminal — its stdout IS the terminal, so
    routine log records (e.g. config_loader's "config loaded" on every
    command) would otherwise interleave with actual command output and
    break any attempt to pipe/redirect it cleanly. Diagnostics to stderr,
    results to stdout is the standard split.

    prog_name="sask" pins the name Typer/Click shows in `Usage:`/help text
    regardless of how this process was actually launched — a real
    pip/poetry-installed console script (dev: `poetry run sask`) already
    reports "sask" on its own, but a plain-module invocation (the droplet's
    /usr/local/bin/sask wrapper runs `python3 -m sask.cli`, since the
    droplet never pip-installs the sask package itself) would otherwise
    show "python -m sask.cli" — Click's own behavior for -m invocations.
    Pinning it keeps --help identical in both environments regardless of
    which underlying mechanism is running it.
    """
    logsetup.configure(stream=sys.stderr)
    app(prog_name="sask")


if __name__ == "__main__":
    main()
