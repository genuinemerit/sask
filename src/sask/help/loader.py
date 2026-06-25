"""Help topic discovery and Markdown rendering (DD-0018, SPEC-030).

Flask-free. discover_topics() is the only startup I/O (a directory
listing); render_markdown() reads and renders fresh per call, with no
caching, per DD-0018's render_timing rationale.
"""

from __future__ import annotations

from pathlib import Path

import markdown

_EXTENSIONS = ["fenced_code", "tables", "toc"]

_INDEX_STEM = "index"


def discover_topics(help_dir: Path) -> dict[str, Path]:
    """Scan help_dir for *.md files and return {stem: resolved_path}.

    The "index" stem is deliberately excluded: index.md is intro content
    for the help index page, not a selectable topic, so it is never
    reachable at /help/index and never appears in the topic list.
    """
    return {
        path.stem: path.resolve()
        for path in sorted(help_dir.glob("*.md"))
        if path.stem != _INDEX_STEM
    }


def index_path(help_dir: Path) -> Path | None:
    """Return the resolved path to index.md if present, else None."""
    candidate = help_dir / "index.md"
    return candidate.resolve() if candidate.is_file() else None


def render_markdown(path: Path) -> str:
    """Read path fresh and render it to HTML with the configured extensions."""
    text = path.read_text(encoding="utf-8")
    return markdown.markdown(text, extensions=_EXTENSIONS)
