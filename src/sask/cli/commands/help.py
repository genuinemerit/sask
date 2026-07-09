"""`sask help [topic]` (DD-0021, REQ-FUN-014, SPEC-034).

Renders help content from the SAME Markdown source the web /help route
renders to HTML (sask.help.loader) — one source, two adapters.
"""

from __future__ import annotations

from pathlib import Path

import typer

from sask.help.loader import discover_topics, index_path

from .._paths import default_help_dir


def _render_help(topic: str | None, help_dir: Path) -> str:
    """Resolve topic to its raw Markdown text; raises typer.Exit(1) if unavailable."""
    topics = discover_topics(help_dir)

    if topic is None:
        index = index_path(help_dir)
        if index is None:
            typer.echo("No help index available.", err=True)
            raise typer.Exit(1)
        text = index.read_text(encoding="utf-8")
        if topics:
            text += "\n\nTopics: " + ", ".join(sorted(topics))
        return text

    path = topics.get(topic)
    if path is None:
        available = ", ".join(sorted(topics)) if topics else "(none)"
        typer.echo(
            f"Error: unknown help topic {topic!r}. Available: {available}", err=True
        )
        raise typer.Exit(1)
    return path.read_text(encoding="utf-8")


def help_command(
    topic: str | None = typer.Argument(
        None, help="Help topic name; omit for the index"
    ),
) -> None:
    """Print help content from the same Markdown source the web /help route uses.

    Example usage:
    `sask help`
    `sask help calendar-lore`
    """
    typer.echo(_render_help(topic, default_help_dir()))
