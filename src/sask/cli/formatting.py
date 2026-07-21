"""Shared CLI output-formatting helpers (DD-0021, DD-0025, SPEC-034, SPEC-038).

Adapter concern: formatting lives here, not in the engine. rich (DD-0025,
DEBT-0003) renders styled output IN A TERMINAL only; when stdout/stderr is
not a terminal (piped/redirected) every helper here prints the exact same
plain text SPEC-034 always has — not merely de-colored rich output, since
rich's own table/panel glyphs would still change the byte stream and could
break scripting against this output. Styling is strictly additive.
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

_console = Console()
_err_console = Console(stderr=True)


def echo_dict(title: str, data: dict[str, object]) -> None:
    """Print a title line, then each key/value pair aligned to one width.

    Generalized from the legacy CLI's version.py::echo_dict. Renders as a
    rich Table in a terminal; identical to the pre-rich plain-text layout
    when piped/redirected.
    """
    if not _console.is_terminal:
        typer.echo(f"\n{title}:")
        if not data:
            typer.echo("  (none)")
            return
        width = max(len(str(key)) for key in data)
        for key, value in data.items():
            typer.echo(f"  {str(key):{width}}: {value}")
        return

    table = Table(title=title, show_header=False)
    table.add_column("field", style="bold cyan")
    table.add_column("value")
    if not data:
        table.add_row("(none)", "")
    else:
        for key, value in data.items():
            table.add_row(str(key), str(value))
    _console.print(table)


def echo_error(message: str) -> None:
    """Print an error message to stderr, for consistent use before typer.Exit(1)."""
    if _err_console.is_terminal:
        _err_console.print(f"[bold red]Error:[/bold red] {message}")
    else:
        typer.echo(f"Error: {message}", err=True)
