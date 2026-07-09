"""Shared config-loading helper for CLI commands (DD-0021, SPEC-034).

Both `convert` and `config check` need an AppConfig loaded the same way
create_app loads one (src/sask/web/__init__.py) — centralized here rather
than duplicated across command modules.
"""

from __future__ import annotations

from pathlib import Path

from sask.config_loader import AppConfig, load_config

from ._paths import default_config_dir


def resolve_and_load_config(config_dir: Path | None = None) -> AppConfig:
    """Load AppConfig from config_dir, defaulting the same way create_app does.

    assets_dir is intentionally not threaded through here — load_config()
    derives its own default (a sibling of config_dir) when omitted, same as
    create_app's own call.
    """
    return load_config(config_dir or default_config_dir())
