"""`sask logs query` / `sask logs verify` (DD-0021, REQ-OPS-020, SPEC-034,
DD-0025, DEBT-0001, SPEC-038).

Admin-tier diagnostics: read-only journal query/verification, uniform in dev
(SPEC-033's systemd user service / sask-dev journal) and prod (sask.service
journal, run on the droplet via SSH). No service mutation.
"""

from __future__ import annotations

import json
import subprocess

import typer

from ..formatting import echo_dict

app = typer.Typer(help="Journal query and verification (read-only)")

# DEBT-0001 — the app-output-checking half of the retired verify-logging.sh:
# at least one well-formed app JSON record, and no cleartext secret, in the
# inspected window. Needles match verify-logging.sh's own REMOTE_CHECK
# exactly (a static pattern scan of arbitrary journal text, not the
# structured-field redaction logsetup.py's SENSITIVE_ENV_VARS drives).
_REQUIRED_JSON_KEYS = ("timestamp", "level", "logger", "message")
_SECRET_NEEDLES = ("DIGITALOCEAN_TOKEN", "dop_v1_")


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
    the droplet (via SSH), reads the same production journal `logs verify`
    inspects. Read-only; no service mutation.

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


def _line_is_wellformed_app_json(line: str) -> bool:
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        return False  # e.g. gunicorn's own plain-text startup notices — expected
    return all(key in record for key in _REQUIRED_JSON_KEYS)


def _line_has_cleartext_secret(line: str) -> bool:
    return any(needle in line and "REDACTED" not in line for needle in _SECRET_NEEDLES)


@app.command("verify")
def logs_verify(
    unit: str = typer.Option("sask", "--unit", help="systemd unit name"),
    user_scope: bool = typer.Option(
        False,
        "--user",
        help="Inspect the user journal (dev: --unit sask-dev) instead of the "
        "system journal (prod: --unit sask, run on the droplet)",
    ),
    lines: int = typer.Option(
        50, "-n", "--lines", help="Number of recent lines to inspect"
    ),
) -> None:
    """Verify recent journal output: well-formed app JSON present, no cleartext secrets.

    DEBT-0001 — the app-output-checking half of the retired
    tools/ops/verify-logging.sh, reusing `logs query`'s journalctl-wrapping
    machinery, now running against whichever journal the CLI's own
    environment has (local, no SSH) rather than SSH-only.

    Example usage:
    `sask logs verify --user --unit sask-dev`
    `sask logs verify -n 200`
    """
    argv = _build_journalctl_argv(unit, user_scope, None, None, lines)
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

    raw_lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    json_ok = sum(1 for ln in raw_lines if _line_is_wellformed_app_json(ln))
    secret_hits = sum(1 for ln in raw_lines if _line_has_cleartext_secret(ln))

    echo_dict(
        "Log verification",
        {
            "total": len(raw_lines),
            "well_formed_json": json_ok,
            "secret_hits": secret_hits,
        },
    )

    if json_ok == 0 or secret_hits:
        typer.echo(
            "Error: no well-formed app JSON found, or a cleartext secret was found.",
            err=True,
        )
        raise typer.Exit(1)
    typer.echo("PASS")
