"""Shared thin-subprocess-wrap helper for CLI commands (DD-0025, SPEC-038).

Admin/dev commands that wrap an existing tools/ script invoke it via this
helper rather than reimplementing its logic — the same "no behavior change"
discipline SPEC-034's logs.py already applies to journalctl. Stdio is
inherited (not captured) so long-running tools (pytest, pre-commit-check)
stream output live, exactly as running the script directly would.
"""

from __future__ import annotations

import subprocess

import typer

from ._paths import repo_root


def run_tool(argv: list[str], env: dict[str, str] | None = None) -> None:
    """Run argv against the repo root; propagate its exit code via typer.Exit.

    A missing tool (e.g. tools/ is not deployed to production — see
    ansible/roles/app/tasks/main.yml) raises FileNotFoundError, reported
    cleanly rather than crashing, matching logs.py's existing "journalctl not
    found" handling.
    """
    try:
        result = subprocess.run(argv, cwd=repo_root(), env=env, check=False)
    except FileNotFoundError as exc:
        typer.echo(f"Error: {exc.filename or argv[0]} not found.", err=True)
        raise typer.Exit(1) from None
    raise typer.Exit(result.returncode)
