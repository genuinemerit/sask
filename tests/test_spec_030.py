"""SPEC-030 tests — help guide: Markdown loader, web routes, starter skeleton.

Covers:
  - discover_topics finds the starter topic, excludes "index"
  - index_path finds docs/help/index.md
  - render_markdown applies the configured extensions (table, fenced code)
  - layer-purity: src/sask/help/loader.py imports no flask
  - GET /help renders 200, intro content, and a link to the starter topic
  - GET /help/getting-started renders 200, wrapped in base.html, with a
    rendered table and code block
  - GET /help/<unknown> returns 404, wrapped in base.html
  - a traversal-style topic value is never a resolvable key (path safety)
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from sask.help.loader import discover_topics, index_path, render_markdown
from sask.web import create_app

PROJECT_ROOT = Path(__file__).parent.parent
REAL_HELP_DIR = PROJECT_ROOT / "docs" / "help"
REAL_CONFIG = PROJECT_ROOT / "config"


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def app():
    return create_app(config_dir=REAL_CONFIG)


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


# ── Topic discovery ──────────────────────────────────────────────────────────


def test_discover_topics_finds_getting_started():
    topics = discover_topics(REAL_HELP_DIR)
    assert "getting-started" in topics
    assert topics["getting-started"] == (REAL_HELP_DIR / "getting-started.md").resolve()


def test_discover_topics_excludes_index():
    topics = discover_topics(REAL_HELP_DIR)
    assert "index" not in topics


def test_index_path_finds_index_md():
    assert index_path(REAL_HELP_DIR) == (REAL_HELP_DIR / "index.md").resolve()


def test_index_path_none_when_absent(tmp_path):
    assert index_path(tmp_path) is None


# ── render_markdown ───────────────────────────────────────────────────────────


def test_render_markdown_applies_table_extension(tmp_path):
    md = tmp_path / "t.md"
    md.write_text("| a | b |\n| --- | --- |\n| 1 | 2 |\n")
    html = render_markdown(md)
    assert "<table>" in html


def test_render_markdown_applies_fenced_code_extension(tmp_path):
    md = tmp_path / "t.md"
    md.write_text("```python\nx = 1\n```\n")
    html = render_markdown(md)
    assert "<pre>" in html or "<code>" in html


def test_render_markdown_reads_fresh_not_cached(tmp_path):
    md = tmp_path / "t.md"
    md.write_text("one")
    first = render_markdown(md)
    md.write_text("two")
    second = render_markdown(md)
    assert "one" in first
    assert "two" in second


# ── Layer purity ──────────────────────────────────────────────────────────────


def _flask_imports_in(path: Path) -> list[str]:
    """Return a list of flask-related import lines found in path."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "flask" in alias.name.lower():
                    found.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if "flask" in module.lower():
                found.append(f"from {module} import ...")
    return found


def test_help_loader_has_no_flask_import():
    hits = _flask_imports_in(PROJECT_ROOT / "src" / "sask" / "help" / "loader.py")
    assert hits == [], f"src/sask/help/loader.py contains flask imports: {hits}"


# ── HTML adapter ──────────────────────────────────────────────────────────────


def test_help_index_returns_200_with_intro_and_topic_link(client):
    resp = client.get("/help")
    assert resp.status_code == 200
    assert b"Welcome to the" in resp.data
    assert b'href="/help/getting-started"' in resp.data


def test_help_topic_returns_200_wrapped_in_base_with_table_and_code(client):
    resp = client.get("/help/getting-started")
    assert resp.status_code == 200
    assert b'href="/help">Help</a>' in resp.data  # base.html nav present
    assert b"<table>" in resp.data
    assert b"<pre>" in resp.data or b"<code>" in resp.data


def test_help_unknown_topic_returns_404_wrapped_in_base(client):
    resp = client.get("/help/nonexistent-topic")
    assert resp.status_code == 404
    assert b'href="/help">Help</a>' in resp.data  # still base.html, not a bare 404
    assert b"not found" in resp.data.lower()


def test_help_topic_route_never_constructs_a_path_from_unknown_input(app):
    # The route's only lookup mechanism is dict membership against the
    # startup-built map; a traversal-style value is simply not a key,
    # regardless of what the URL layer itself does with embedded slashes.
    with app.test_request_context():
        topic_map = app.config["SASK_HELP_TOPICS"]
        assert topic_map.get("../devlog") is None
        assert topic_map.get("..") is None
        assert topic_map.get("/etc/passwd") is None
