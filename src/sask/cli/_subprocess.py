"""Shared thin-subprocess-wrap helper for CLI commands (DD-0025, SPEC-038).

Admin/dev commands that wrap an existing tools/ script invoke it via this
helper rather than reimplementing its logic — the same "no behavior change"
discipline SPEC-034's logs.py already applies to journalctl. Stdio is
inherited (not captured) so long-running tools (pytest, pre-commit-check)
stream output live, exactly as running the script directly would.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import typer

from ._paths import repo_root


def run_tool(
    launcher: list[str],
    script: Path,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
) -> None:
    """Run launcher + [script] + args; propagate its exit code via typer.Exit.

    script is checked for existence explicitly first, rather than relying
    on subprocess.run to raise — caught live during SPEC-038 prod UAT:
    subprocess.run(["bash", missing_path]) does NOT raise Python's
    FileNotFoundError (bash itself is found on PATH; only ITS argument is
    missing), so a bare try/except FileNotFoundError around subprocess.run
    never actually catches "tools/ isn't part of the deployed package" (see
    ansible/roles/app/tasks/main.yml) — bash prints its own raw "No such
    file or directory" instead. Checking script.exists() first gives a
    clear, actionable message in exactly that case. The except below still
    guards the rarer case where the launcher itself (bash/python3) isn't on
    PATH at all.
    """
    if not script.exists():
        typer.echo(
            f"Error: {script} not found — this command needs a full sask "
            "checkout (tools/ is not part of the deployed package).",
            err=True,
        )
        raise typer.Exit(1)

    argv = [*launcher, str(script), *(args or [])]
    try:
        result = subprocess.run(argv, cwd=repo_root(), env=env, check=False)
    except FileNotFoundError as exc:
        typer.echo(f"Error: {exc.filename or argv[0]} not found.", err=True)
        raise typer.Exit(1) from None
    raise typer.Exit(result.returncode)
