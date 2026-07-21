"""`sask help [topic]` (DD-0021, REQ-FUN-014, SPEC-034, DD-0022/SPEC-035, DD-0025).

Renders help content from the SAME Markdown source the web /help route
renders to HTML (sask.help.loader) — one source, two adapters. Locale-
specific parallel documents (DD-0022) are selected the same way the web
route does: (topic, bound locale) looked up against the known set built
at startup, falling back to the base document on a miss.

rich (DD-0025) renders the Markdown styled in a terminal; piped/redirected
output stays the exact raw Markdown source (unchanged from SPEC-034), so
scripting against `sask help` output is unaffected.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown

from sask.help.loader import discover_parallel_docs, discover_topics, index_path

from .._paths import default_help_dir

_console = Console()


def _render_help(topic: str | None, locale: str, help_dir: Path) -> str:
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

    parallel_docs = discover_parallel_docs(help_dir)
    path = parallel_docs.get((topic, locale)) or topics.get(topic)
    if path is None:
        available = ", ".join(sorted(topics)) if topics else "(none)"
        typer.echo(
            f"Error: unknown help topic {topic!r}. Available: {available}", err=True
        )
        raise typer.Exit(1)
    return path.read_text(encoding="utf-8")


def help_command(
    ctx: typer.Context,
    topic: str | None = typer.Argument(
        None, help="Help topic name; omit for the index"
    ),
) -> None:
    """Print help content from the same Markdown source the web /help route uses.

    Example usage:
    `sask help`
    `sask help calendar-lore`
    `sask --lang es-ES help getting-started`
    """
    lang = (ctx.obj or {}).get("lang") if ctx.obj else None
    # A bare default here (not cfg.i18n.base_locale) since help_command has
    # no config load of its own; an unknown/absent locale simply never
    # matches a parallel doc key and falls back to the base document,
    # which is the correct behavior either way.
    locale = lang or "en-US"
    text = _render_help(topic, locale, default_help_dir())
    if _console.is_terminal:
        _console.print(Markdown(text))
    else:
        typer.echo(text)
