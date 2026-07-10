"""Help topic discovery and Markdown rendering (DD-0018, SPEC-030, DD-0022/SPEC-035).

Flask-free. discover_topics()/discover_parallel_docs() are the only
startup I/O (directory listings); render_markdown() reads and renders
fresh per call, with no caching, per DD-0018's render_timing rationale.
"""

from __future__ import annotations

import re
from pathlib import Path

import markdown

_EXTENSIONS = ["fenced_code", "tables", "toc"]

_INDEX_STEM = "index"

# Parallel-locale doc naming: "{topic}.{locale}.md", e.g. "getting-started.es-ES.md"
# (DD-0022). A locale looks like "es-ES" -- two lowercase letters, a hyphen, two
# uppercase letters -- distinguishing it from a plain topic stem.
_LOCALE_SUFFIX_RE = re.compile(r"^[a-z]{2}-[A-Z]{2}$")


def _split_locale_suffix(stem: str) -> tuple[str, str | None]:
    """Split 'topic.locale' into (topic, locale); (stem, None) if no locale suffix."""
    if "." in stem:
        head, _, tail = stem.rpartition(".")
        if _LOCALE_SUFFIX_RE.match(tail):
            return head, tail
    return stem, None


def discover_topics(help_dir: Path) -> dict[str, Path]:
    """Scan help_dir for base (non-locale-suffixed) *.md files.

    Returns {stem: resolved_path}. The "index" stem is deliberately
    excluded: index.md is intro content for the help index page, not a
    selectable topic, so it is never reachable at /help/index and never
    appears in the topic list. Locale-suffixed files (see
    discover_parallel_docs) are excluded here too -- they are not base
    topics in their own right.
    """
    result: dict[str, Path] = {}
    for path in sorted(help_dir.glob("*.md")):
        topic, locale = _split_locale_suffix(path.stem)
        if locale is not None or topic == _INDEX_STEM:
            continue
        result[topic] = path.resolve()
    return result


def discover_parallel_docs(help_dir: Path) -> dict[tuple[str, str], Path]:
    """Scan help_dir for {topic}.{locale}.md files (DD-0022, REQ-SEC-005).

    Returns {(topic, locale): resolved_path} -- a known set built once at
    startup, mirroring discover_topics()'s and the asset catalog's
    resolved-path pattern. A locale value is only ever used as a dict key
    against this set; it is never path-joined into a filesystem read, so a
    crafted/traversal locale value cannot escape this known set.
    """
    result: dict[tuple[str, str], Path] = {}
    for path in sorted(help_dir.glob("*.md")):
        topic, locale = _split_locale_suffix(path.stem)
        if locale is None:
            continue
        result[(topic, locale)] = path.resolve()
    return result


def index_path(help_dir: Path) -> Path | None:
    """Return the resolved path to index.md if present, else None."""
    candidate = help_dir / "index.md"
    return candidate.resolve() if candidate.is_file() else None


def render_markdown(path: Path) -> str:
    """Read path fresh and render it to HTML with the configured extensions."""
    text = path.read_text(encoding="utf-8")
    return markdown.markdown(text, extensions=_EXTENSIONS)
