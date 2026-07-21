"""Shared domain-identifier -> i18n-tag mappings (DD-0022, SPEC-035).

Holds only mappings genuinely shared across adapters (web AND cli).
Web-only display mappings (e.g. translator.py's moon-phase/compass
tables) stay local to translator.py — this module is not a dumping
ground for every lookup table, only the ones more than one adapter needs.
"""

from __future__ import annotations


def season_tag(season_id: str) -> str:
    """Map a SeasonInfo.season_id (engine domain identifier) to its i18n tag.

    Uniformly 1:1 (see analysis/i18n-content-inventory.md) -- the engine
    emits the identifier, this is the thin render-layer DD-0022
    anticipates, mapping identifier -> tag before the resolver runs.
    """
    return f"season.{season_id}"


def event_tag(event_id: str) -> str:
    """Map a SeasonInfo.near_event_id (engine domain identifier) to its i18n tag."""
    return f"event.{event_id}"
