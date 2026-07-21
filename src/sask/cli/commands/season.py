"""`sask season --pulse N` (DD-0021, DD-0022, REQ-FUN-014, REQ-FUN-015, SPEC-035).

Wraps sask.calendar.season.season_info() — the same function the web
`/sky` route calls — returning the same SeasonInfo message unit. The
i18n canary's "one message unit, many locales, many adapters" proof: the
displayed season name is resolved from the same shared catalog the web
adapter's /sky page draws from, for whichever locale is bound
(--lang/SASK_LOCALE); season_id itself stays a locale-neutral engine
identifier throughout.
"""

from __future__ import annotations

import typer

from sask.calendar.season import season_info
from sask.i18n.catalog import resolve
from sask.i18n.tags import event_tag, season_tag

from .._config import resolve_and_load_config
from ..formatting import echo_dict


def season(
    ctx: typer.Context,
    pulse: int = typer.Option(..., "--pulse", "-p", help="Raw pulse value"),
) -> None:
    """Show the astronomical season (and near-event) for a pulse, localized.

    Example usage:
    `sask season --pulse 0`
    `sask --lang es-ES season --pulse 0`
    """
    cfg = resolve_and_load_config()
    lang = (ctx.obj or {}).get("lang") if ctx.obj else None
    locale = lang if lang in cfg.i18n.locales else cfg.i18n.base_locale

    info = season_info(pulse, cfg)
    name = resolve(season_tag(info.season_id), locale, cfg.i18n)
    near_event_name = (
        resolve(event_tag(info.near_event_id), locale, cfg.i18n)
        if info.near_event_id
        else None
    )

    echo_dict(
        "Season",
        {
            "season_id": info.season_id,
            "name": name,
            "near_event_name": near_event_name or "—",
            "locale": locale,
        },
    )
