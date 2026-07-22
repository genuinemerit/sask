"""Default filesystem paths for the CLI (DD-0021, SPEC-034).

Centralized here, at the same directory depth as src/sask/web/__init__.py
(cli/ is a sibling of web/, both directly under src/sask/), so every command
module resolves paths the same way without each re-deriving its own walk-up
depth — the exact class of off-by-one bug the SPEC-029 tools/ reorg hit when
moved files sat one directory level deeper than their old path math assumed.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def repo_root() -> Path:
    return _REPO_ROOT


def default_config_dir() -> Path:
    return _REPO_ROOT / "config"


def default_help_dir() -> Path:
    return _REPO_ROOT / "docs" / "help"


def has_tools_ops() -> bool:
    """True when tools/ops/ exists relative to repo_root() — i.e. this is a
    full checkout, not the deployed package (ansible/roles/app/tasks/main.yml
    only syncs src/sask/, config/, assets, docs/help/, wsgi.py; tools/ is
    deliberately excluded, DD-0021's ops-vs-CLI boundary). Used to hide
    CLI commands that subprocess-wrap a tools/ops/ script (acceptance-test,
    run_perf) from --help where they could never succeed, rather than
    leaving them visible only to fail with a clean error on every attempt.
    """
    return (_REPO_ROOT / "tools" / "ops").is_dir()
