"""`sask config check` (DD-0021, REQ-FUN-014, SPEC-034).

Admin-tier diagnostic: read-only, on-demand config validation. Does not
mutate anything.
"""

from __future__ import annotations

from pathlib import Path

import typer

from sask.config_loader import ConfigError

from .._config import resolve_and_load_config
from ..formatting import echo_dict

app = typer.Typer(help="Config validation (read-only)")


@app.command("check")
def config_check(
    config_dir: Path | None = typer.Option(
        None,
        "--config-dir",
        help="Override the config directory (defaults like create_app)",
    ),
) -> None:
    """Validate config the same way create_app() does, and report the outcome.

    Example usage:
    `sask config check`
    """
    try:
        cfg = resolve_and_load_config(config_dir)
    except ConfigError as exc:
        typer.echo(f"Error: config invalid: {exc}", err=True)
        raise typer.Exit(1) from None

    echo_dict(
        "Config OK",
        {
            "bodies": len(cfg.bodies),
            "stars": len(cfg.stars),
            "houses": len(cfg.houses),
            "comets": len(cfg.comets),
            "lunar_calendars": len(cfg.lunar_calendars),
            "sky_styles": len(cfg.sky_styles),
            "lore_calendars": len(cfg.lore_calendars),
            "assets": len(cfg.asset_catalog.entries),
        },
    )
