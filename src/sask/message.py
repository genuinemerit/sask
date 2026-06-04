"""Message-unit dataclasses for the sask engine (REQ-OPS-008).

All message units are frozen dataclasses with snake_case fields.
Downstream callers (UI, tests) import only from this module — never
from internal engine modules directly.
"""

from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(frozen=True)
class PulseInfo:
    """Core quantities derived from a raw pulse (SPEC-002)."""

    pulse: int
    astro_day: int
    day_pulse_offset: int  # pulses elapsed since Astro midnight [0, 86400)
    orbital_position: float  # AstroYear position [0.0, 1.0)


@dataclass(frozen=True)
class CalendarDate:
    """A date expressed in one specific calendar (scaffold for SPEC-003)."""

    calendar_id: str  # "astro" | "fatunik" | "terpin"
    year: int
    month: int
    day: int


@dataclass(frozen=True)
class SeasonInfo:
    """Astronomical season and event proximity for a pulse (SPEC-004)."""

    season_id: str  # "greening" | "blazing" | "withering" | "stillness"
    name: str
    orbital_position: float  # position within the AstroYear [0.0, 1.0)
    near_event_id: str | None = None  # event id if within near_tolerance
    near_event_name: str | None = None  # display name of the near event


@dataclass(frozen=True)
class BodyState:
    """State of a celestial body at a given pulse (SPEC-007).

    All angles in degrees; times in pulses; distances in body-type units
    (km for moons, AU for planets). Brightness and apparent_size are
    dimensionless relative scalars — meaningful for comparison within a
    category, not for cross-category comparison.
    """

    name: str
    body_type: str  # "moon" | "planet"
    sidereal_fraction: float  # [0.0, 1.0) — position in sidereal orbit
    ecliptic_lon_deg: float  # [0.0, 360.0) — geocentric ecliptic longitude
    ecliptic_lat_deg: float  # (-90.0, 90.0) — geocentric ecliptic latitude
    geocentric_dist: float  # km (moons) or AU (planets)
    synodic_fraction: float  # [0.0, 1.0); 0=conjunction/new, 0.5=opposition/full
    illuminated_fraction: float  # [0.0, 1.0] — fraction of visible face lit by Fatune
    visibility: float  # [0.0, 1.0]; 0 when lost in glare or Gavor's shadow
    is_visible: bool
    eclipse_type: str | None  # "solar" | "lunar" | None
    apparent_size: float  # diameter_km / geocentric_dist_km (dimensionless)
    brightness: float  # albedo × illuminated_fraction × apparent_size (relative)


def validate(unit: object) -> list[str]:
    """Return a list of field-level errors for a message-unit dataclass.

    Checks that no required field (any field whose type is not Optional)
    holds None.  Returns an empty list when the unit is valid.
    """
    errors: list[str] = []
    for f in fields(unit):  # type: ignore[arg-type]
        value = getattr(unit, f.name)
        if value is None:
            errors.append(f"{type(unit).__name__}.{f.name} must not be None")
    return errors
