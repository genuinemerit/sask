"""SASK_ENV dev/non-dev signal (DD-0025, REQ-FUN-017, SPEC-038).

Read once per process, the same way logsetup.py reads SASK_LOG_LEVEL — the
CLI is a fresh process per invocation, so there is no staleness concern.
Dev-tier commands are the one tier DD-0025 enforces now (player/admin stay
tagged-but-unenforced until auth exists): "is this a dev environment" is
knowable from the environment alone, unlike "is this user an admin."
"""

from __future__ import annotations

import os

import typer

_DEV_ONLY_MESSAGE = (
    "Error: this command is available only in a development environment "
    "(set SASK_ENV=dev)."
)


def is_dev_env() -> bool:
    return os.environ.get("SASK_ENV", "").strip().lower() == "dev"


def require_dev() -> None:
    """Raise typer.Exit(1) with a clean stderr message outside a dev environment.

    Called at the top of every dev-tier command body as defense in depth —
    cli/__init__.py already hides these commands from --help outside dev via
    hidden=not is_dev_env(), but a command invoked directly by name must
    still refuse cleanly rather than run.
    """
    if not is_dev_env():
        typer.echo(_DEV_ONLY_MESSAGE, err=True)
        raise typer.Exit(1)
