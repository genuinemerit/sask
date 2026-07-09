"""`sask logs query` (DD-0021, REQ-OPS-020, SPEC-034).

Admin-tier diagnostic: read-only journal query, uniform in dev (SPEC-033's
systemd user service / sask-dev journal) and prod (sask.service journal, run
on the droplet via SSH). No service mutation.
"""

from __future__ import annotations

import json
import subprocess

import typer

app = typer.Typer(help="Journal query (read-only)")


def _build_journalctl_argv(
    unit: str,
    user_scope: bool,
    since: str | None,
    grep: str | None,
    lines: int,
) -> list[str]:
    """Build a journalctl argv list. Never a shell string — grep/since/unit are
    each a single, literal argv element, so shell metacharacters in any of
    them are inert (subprocess.run receives this list with shell=False).
    """
    argv = ["journalctl"]
    if user_scope:
        argv.append("--user")
    argv += ["-u", unit, "--no-pager", "-n", str(lines)]
    if since:
        argv += ["--since", since]
    if grep:
        argv += ["--grep", grep]
    return argv


def _line_matches_level(line: str, level: str) -> bool:
    """True only for a well-formed app JSON line whose "level" field matches.

    Non-JSON lines (e.g. gunicorn's own plain-text notices) never match a
    level filter — they have no level to match against.
    """
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        return False
    return str(record.get("level", "")).upper() == level.upper()


@app.command("query")
def logs_query(
    level: str | None = typer.Option(
        None,
        "--level",
        help="Show only structured app records at this level (INFO, ERROR, ...)",
    ),
    since: str | None = typer.Option(
        None, "--since", help="journalctl --since value, e.g. '1 hour ago'"
    ),
    grep: str | None = typer.Option(
        None, "--grep", help="Pattern passed to journalctl --grep"
    ),
    unit: str = typer.Option("sask", "--unit", help="systemd unit name"),
    user_scope: bool = typer.Option(
        False,
        "--user",
        help="Query the user journal (dev: --unit sask-dev) instead of the "
        "system journal (prod: --unit sask, run on the droplet)",
    ),
    lines: int = typer.Option(100, "-n", "--lines", help="Number of lines to retrieve"),
) -> None:
    """Query the sask service's journal — identical behavior in dev and prod.

    In dev, reads the journal SPEC-033's systemd user service writes to. On
    the droplet (via SSH), reads the same production journal
    tools/ops/verify-logging.sh inspects. Read-only; no service mutation.

    Example usage:
    `sask logs query --user --unit sask-dev`
    `sask logs query --level ERROR -n 200`
    """
    argv = _build_journalctl_argv(unit, user_scope, since, grep, lines)
    try:
        result = subprocess.run(argv, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        typer.echo("Error: journalctl not found on this host.", err=True)
        raise typer.Exit(1) from None

    if result.returncode != 0:
        typer.echo(
            result.stderr.strip() or f"journalctl exited {result.returncode}", err=True
        )
        raise typer.Exit(result.returncode)

    output_lines = result.stdout.splitlines()
    if level:
        output_lines = [ln for ln in output_lines if _line_matches_level(ln, level)]
    typer.echo("\n".join(output_lines))
