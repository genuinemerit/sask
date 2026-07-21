"""Presentation translators: message units → view models (SPEC-005, SPEC-009).

Converts raw engine output into display-ready strings. No web-layer dependency
beyond the i18n resolver (locale is an explicit argument throughout, DD-0022 —
never ambient state).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config_loader import I18nCatalog
from ..i18n.catalog import resolve
from ..message import BodyState, PulseInfo, SkyPosition


# ── SPEC-005 ───────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PulseViewModel:
    """Display-ready representation of a PulseInfo result."""

    pulse: int
    astro_day: int
    day_pulse_offset: int
    orbital_position: float
    time_of_day: str  # HH:MM:SS (1 pulse = 1 second, from Astro midnight)
    orbital_position_pct: str  # "25.0000%" of AstroYear elapsed


def to_pulse_view(info: PulseInfo) -> PulseViewModel:
    """Translate a PulseInfo message unit into a PulseViewModel for the template."""
    h = info.day_pulse_offset // 3600
    m = (info.day_pulse_offset % 3600) // 60
    s = info.day_pulse_offset % 60
    return PulseViewModel(
        pulse=info.pulse,
        astro_day=info.astro_day,
        day_pulse_offset=info.day_pulse_offset,
        orbital_position=info.orbital_position,
        time_of_day=f"{h:02d}:{m:02d}:{s:02d}",
        orbital_position_pct=f"{info.orbital_position * 100:.4f}%",
    )


# ── SPEC-009 helpers ───────────────────────────────────────────────────────────

_CARDINAL_TAGS = [
    "compass.n",
    "compass.nne",
    "compass.ne",
    "compass.ene",
    "compass.e",
    "compass.ese",
    "compass.se",
    "compass.sse",
    "compass.s",
    "compass.ssw",
    "compass.sw",
    "compass.wsw",
    "compass.w",
    "compass.wnw",
    "compass.nw",
    "compass.nnw",
]


def _cardinal(az_deg: float, locale: str, i18n: I18nCatalog) -> str:
    tag = _CARDINAL_TAGS[int((az_deg + 11.25) / 22.5) % 16]
    return resolve(tag, locale, i18n)


def _az_str(az_deg: float, locale: str, i18n: I18nCatalog) -> str:
    return f"{az_deg:.1f}° {_cardinal(az_deg, locale, i18n)}"


def _alt_str(alt_deg: float) -> str:
    sign = "+" if alt_deg >= 0 else ""
    return f"{sign}{alt_deg:.1f}°"


def _pulse_str(
    p: int | None,
    circumpolar: bool,
    never_rising: bool,
    locale: str,
    i18n: I18nCatalog,
) -> str:
    if circumpolar:
        return resolve("misc.circumpolar_value", locale, i18n)
    if never_rising:
        return resolve("misc.never_rises", locale, i18n)
    return str(p) if p is not None else "—"


_PHASE_TAGS = (
    (0.03, "phase.new"),
    (0.22, "phase.waxing_crescent"),
    (0.28, "phase.first_quarter"),
    (0.47, "phase.waxing_gibbous"),
    (0.53, "phase.full"),
    (0.72, "phase.waning_gibbous"),
    (0.78, "phase.last_quarter"),
)


def _phase_name(syn: float, locale: str, i18n: I18nCatalog) -> str:
    """Rough phase name from synodic fraction (0=new, 0.5=full)."""
    if syn >= 0.97:
        return resolve("phase.new", locale, i18n)
    for threshold, tag in _PHASE_TAGS:
        if syn < threshold:
            return resolve(tag, locale, i18n)
    return resolve("phase.waning_crescent", locale, i18n)


# ── SPEC-009 moon view model ───────────────────────────────────────────────────


@dataclass(frozen=True)
class MoonViewModel:
    """Display-ready state of one moon for the sky view."""

    name: str
    phase_name: str
    illuminated_pct: str  # "87.3%"
    albedo: str  # "0.350"
    is_visible: bool
    visibility_pct: str  # "0.0%" or "65.4%"
    eclipse: str  # "Solar", "Lunar", or "—"
    altitude: str  # "+42.1°" or "−18.6°"
    azimuth: str  # "135.7° SE"
    above_horizon: bool
    rise_pulse: str
    transit_pulse: str
    set_pulse: str
    notes: str


_ECLIPSE_TAGS = {"solar": "misc.eclipse_solar", "lunar": "misc.eclipse_lunar"}


def to_moon_view(
    body: BodyState,
    sky: SkyPosition,
    albedo: float,
    locale: str,
    i18n: I18nCatalog,
) -> MoonViewModel:
    eclipse = (
        resolve(_ECLIPSE_TAGS[body.eclipse_type], locale, i18n)
        if body.eclipse_type
        else "—"
    )
    return MoonViewModel(
        name=resolve(f"body.{body.name.lower()}", locale, i18n),
        phase_name=_phase_name(body.synodic_fraction, locale, i18n),
        illuminated_pct=f"{body.illuminated_fraction * 100:.1f}%",
        albedo=f"{albedo:.3f}",
        is_visible=body.is_visible and sky.above_horizon,
        visibility_pct=f"{body.visibility * 100:.1f}%",
        eclipse=eclipse,
        altitude=_alt_str(sky.altitude_deg),
        azimuth=_az_str(sky.azimuth_deg, locale, i18n),
        above_horizon=sky.above_horizon,
        rise_pulse=_pulse_str(
            sky.rise_pulse, sky.is_circumpolar, sky.is_never_rising, locale, i18n
        ),
        transit_pulse=str(sky.transit_pulse),
        set_pulse=_pulse_str(
            sky.set_pulse, sky.is_circumpolar, sky.is_never_rising, locale, i18n
        ),
        notes=resolve(f"body.{body.name.lower()}.notes", locale, i18n),
    )


# ── SPEC-009 planet view model ─────────────────────────────────────────────────


@dataclass(frozen=True)
class PlanetViewModel:
    """Display-ready state of one planet for the sky view."""

    name: str
    apparent_color: str
    phase_name: str
    illuminated_pct: str
    is_visible: bool
    visibility_pct: str
    altitude: str
    azimuth: str
    above_horizon: bool
    rise_pulse: str
    transit_pulse: str
    set_pulse: str
    brightness_rel: str  # relative scalar rounded to 4 d.p.
    rings: str  # descriptive text or "None"
    visible_moons: str  # "4" or "0"
    notes: str


def to_planet_view(
    body: BodyState,
    sky: SkyPosition,
    rings: str | None,
    visible_moons: int | None,
    locale: str,
    i18n: I18nCatalog,
) -> PlanetViewModel:
    body_id = body.name.lower()
    rings_str = (
        resolve(f"body.{body_id}.rings", locale, i18n)
        if rings and rings.lower() != "none"
        else "None"
    )
    moons_str = str(visible_moons) if visible_moons is not None else "0"
    return PlanetViewModel(
        name=resolve(f"body.{body_id}", locale, i18n),
        apparent_color=resolve(f"body.{body_id}.color", locale, i18n),
        phase_name=_phase_name(body.synodic_fraction, locale, i18n),
        illuminated_pct=f"{body.illuminated_fraction * 100:.1f}%",
        is_visible=body.is_visible and sky.above_horizon,
        visibility_pct=f"{body.visibility * 100:.1f}%",
        altitude=_alt_str(sky.altitude_deg),
        azimuth=_az_str(sky.azimuth_deg, locale, i18n),
        above_horizon=sky.above_horizon,
        rise_pulse=_pulse_str(
            sky.rise_pulse, sky.is_circumpolar, sky.is_never_rising, locale, i18n
        ),
        transit_pulse=str(sky.transit_pulse),
        set_pulse=_pulse_str(
            sky.set_pulse, sky.is_circumpolar, sky.is_never_rising, locale, i18n
        ),
        brightness_rel=f"{body.brightness:.4f}",
        rings=rings_str,
        visible_moons=moons_str,
        notes=resolve(f"body.{body_id}.notes", locale, i18n),
    )
