"""Typer CLI consumer adapter for sask (DD-0021, REQ-FUN-014, SPEC-034).

Thin adapter: each command parses args, calls the same clean-room
engine/spine functions the web adapter calls, and formats output. No domain
logic lives here or in commands/*.py — see
design/analysis/saskan-app-alt-port/legacy-cli-deepening.md for the legacy
anti-pattern this deliberately avoids.

cli/ may import the engine/spine (to call it); the engine/spine must never
import cli/ (layer-purity test, tests/test_spec_034.py).
"""

from __future__ import annotations

import sys

import typer

from sask import logsetup
from sask.cli.commands import asset, calendar, config, help as help_cmd, logs

app = typer.Typer(help="sask calendar-engine CLI", no_args_is_help=True)


@app.callback()
def _root() -> None:
    """sask — Saskan calendar engine CLI."""
    # Required no-op root callback: the legacy CLI's own devlog records a
    # real bug (a subcommand silently broke) when this was omitted. Kept
    # deliberately, not rediscovered — see legacy-cli-deepening.md.


app.command("help")(help_cmd.help_command)
app.command("convert")(calendar.convert)
app.add_typer(asset.app, name="asset")
app.add_typer(config.app, name="config")
app.add_typer(logs.app, name="logs")


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
