"""Shared CLI output-formatting helpers (DD-0021, SPEC-034).

Adapter concern: formatting lives here, not in the engine. Plain
typer.echo()-based text output throughout — see
design/analysis/saskan-app-alt-port/legacy-cli-deepening.md for why no rich
dependency is introduced.
"""

from __future__ import annotations

import typer


def echo_dict(title: str, data: dict[str, object]) -> None:
    """Print a title line, then each key/value pair aligned to one width.

    Generalized from the legacy CLI's version.py::echo_dict.
    """
    typer.echo(f"\n{title}:")
    if not data:
        typer.echo("  (none)")
        return
    width = max(len(str(key)) for key in data)
    for key, value in data.items():
        typer.echo(f"  {str(key):{width}}: {value}")


def echo_error(message: str) -> None:
    """Print an error message to stderr, for consistent use before typer.Exit(1)."""
    typer.echo(f"Error: {message}", err=True)
