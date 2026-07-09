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


def default_config_dir() -> Path:
    return _REPO_ROOT / "config"


def default_help_dir() -> Path:
    return _REPO_ROOT / "docs" / "help"
