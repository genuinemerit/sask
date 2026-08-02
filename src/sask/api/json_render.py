"""JSON adapter: message-unit -> JSON-serializable dict (DD-0026, SPEC-039).

A thin peer to web/translator.py: renders the SAME message units the HTML
adapter renders, following their DATA shape (raw dataclass fields), not
translator.py's display-formatted ViewModels (pre-rounded strings, bucketed
labels like "circumpolar"). No Flask import, no domain logic — pure
functions of already-computed message units plus the i18n resolver, same
discipline as translator.py.

Keys are always English (DD-0026): every dict key below is a fixed English
string regardless of locale. A "localizable domain value" — one the HTML
path already resolves through the i18n catalog via a stable id already
present in the message unit (body name, eclipse type, season, event, house,
star, lunar-calendar id) — renders as {"id": ..., "label": ...} via
id_label(); the id is invariant, the label localizes. Free-text/prose
fields the engine already resolved to a display string (notes, rings
description, night_summary, image_prompt, lore date/time, and every
BodyInScene.direction/color/phase — locale-baked at SkyScene composition
time, see scene.py) pass through as plain localized strings: there is no
separate stable id to switch on for these, so wrapping them would invent
data the message unit doesn't carry.

Two fields deliberately stay plain strings despite naming a calendar:
CalendarDate.calendar_id ("fatunik"/"terpin") has no i18n label tag in the
catalog — only lunar calendar ids do (calendar.<id>_name) — confirmed
against config/i18n/en-US.toml while implementing SPEC-039, not assumed.
"""

from __future__ import annotations

from sask.calendar.ephemeris import EphemerisSeries
from sask.calendar.pulse import (
    astro_to_fatunik,
    astro_to_terpin,
    format_civil_time,
    pulse_info,
)
from sask.config_loader import AppConfig, I18nCatalog, LunarCalendarConfig
from sask.i18n.catalog import resolve
from sask.i18n.tags import event_tag, season_tag
from sask.message import (
    BodyInScene,
    BodyState,
    CalendarDate,
    CofullnessTonightRef,
    HouseRef,
    LunarDate,
    NextCofullnessRef,
    SeasonInfo,
    SkyPosition,
    SkyScene,
    StarInScene,
)

_ECLIPSE_TAGS = {"solar": "misc.eclipse_solar", "lunar": "misc.eclipse_lunar"}


# ── Core {id, label} helper ─────────────────────────────────────────────────


def id_label(id_: str, tag: str, locale: str, i18n: I18nCatalog) -> dict[str, str]:
    """A localizable domain value: invariant id + locale-resolved label."""
    return {"id": id_, "label": resolve(tag, locale, i18n)}


def body_name_json(body_id: str, locale: str, i18n: I18nCatalog) -> dict[str, str]:
    return id_label(body_id, f"body.{body_id}", locale, i18n)


def eclipse_json(
    eclipse_type: str | None, locale: str, i18n: I18nCatalog
) -> dict[str, str] | None:
    if eclipse_type is None:
        return None
    return id_label(eclipse_type, _ECLIPSE_TAGS[eclipse_type], locale, i18n)


# ── Calendar dates ───────────────────────────────────────────────────────────


def calendar_date_json(date: CalendarDate) -> dict:
    """Fatunik/Terpin civil date. calendar_id has no i18n label (see module
    docstring) — kept as a plain invariant string, not {id, label}."""
    return {
        "calendar_id": date.calendar_id,
        "year": date.year,
        "month": date.month,
        "day": date.day,
    }


def lunar_calendar_moon_json(
    moon_id: str, locale: str, i18n: I18nCatalog
) -> dict[str, str]:
    """The moon a lunar calendar tracks — "mean" (Terpin lunar) or a real moon id."""
    if moon_id == "mean":
        return id_label("mean", "misc.mean_moon", locale, i18n)
    return body_name_json(moon_id, locale, i18n)


def lunar_entry_json(
    cal: LunarCalendarConfig, ld: LunarDate, locale: str, i18n: I18nCatalog
) -> dict:
    return {
        "calendar": id_label(cal.id, f"calendar.{cal.id}_name", locale, i18n),
        "moon": lunar_calendar_moon_json(cal.moon, locale, i18n),
        "has_turns": ld.has_turns,
        "lunation": ld.lunation,
        "day": ld.day,
        "month": ld.month,
        "turn": ld.turn,
        "short_count": ld.short_count,
        "long_count": ld.long_count,
    }


def temporal_json(pulse: int, cfg: AppConfig, locale: str) -> dict:
    """DD-0026 temporal contract: resolved pulse + atomic (Astro) date/time,
    always present regardless of the query's date format."""
    info = pulse_info(pulse, cfg)
    ppd = cfg.time_constants.pulses_per_day
    return {
        "pulse": info.pulse,
        "astro_day": info.astro_day,
        "astro_time": format_civil_time(info.day_pulse_offset, ppd),
        "orbital_position": info.orbital_position,
        "fatunik_date": calendar_date_json(astro_to_fatunik(pulse, cfg)),
        "terpin_date": calendar_date_json(astro_to_terpin(pulse, cfg)),
    }


# ── Bodies (BodyState + SkyPosition), /moons and /planets ──────────────────


def body_entry_json(
    state: BodyState,
    sky: SkyPosition,
    *,
    locale: str,
    i18n: I18nCatalog,
    albedo: float | None = None,
    rings: str | None = None,
    visible_moons: int | None = None,
) -> dict:
    """One moon or planet: complete BodyState + SkyPosition, merged per body
    the same way the HTML page's row-per-body table already merges them."""
    body_id = state.name.lower()
    rings_label = (
        resolve(f"body.{body_id}.rings", locale, i18n)
        if rings and rings.lower() != "none"
        else None
    )
    return {
        "name": body_name_json(body_id, locale, i18n),
        "body_type": state.body_type,
        "sidereal_fraction": state.sidereal_fraction,
        "ecliptic_lon_deg": state.ecliptic_lon_deg,
        "ecliptic_lat_deg": state.ecliptic_lat_deg,
        "geocentric_dist": state.geocentric_dist,
        "synodic_fraction": state.synodic_fraction,
        "illuminated_fraction": state.illuminated_fraction,
        "visibility": state.visibility,
        "is_visible": state.is_visible,
        "eclipse_type": eclipse_json(state.eclipse_type, locale, i18n),
        "apparent_size": state.apparent_size,
        "brightness": state.brightness,
        "albedo": albedo,
        "rings": rings_label,
        "visible_moons": visible_moons,
        "notes": resolve(f"body.{body_id}.notes", locale, i18n),
        "declination_deg": sky.declination_deg,
        "right_ascension_deg": sky.right_ascension_deg,
        "altitude_deg": sky.altitude_deg,
        "azimuth_deg": sky.azimuth_deg,
        "above_horizon": sky.above_horizon,
        "is_circumpolar": sky.is_circumpolar,
        "is_never_rising": sky.is_never_rising,
        "transit_pulse": sky.transit_pulse,
        "rise_pulse": sky.rise_pulse,
        "set_pulse": sky.set_pulse,
    }


def sky_position_json(sky: SkyPosition, locale: str, i18n: I18nCatalog) -> dict:
    """A position with no BodyState of its own — Fatune, the star."""
    body_id = sky.name.lower()
    return {
        "name": body_name_json(body_id, locale, i18n),
        "body_type": sky.body_type,
        "declination_deg": sky.declination_deg,
        "right_ascension_deg": sky.right_ascension_deg,
        "altitude_deg": sky.altitude_deg,
        "azimuth_deg": sky.azimuth_deg,
        "above_horizon": sky.above_horizon,
        "is_circumpolar": sky.is_circumpolar,
        "is_never_rising": sky.is_never_rising,
        "transit_pulse": sky.transit_pulse,
        "rise_pulse": sky.rise_pulse,
        "set_pulse": sky.set_pulse,
    }


# ── Season, /sky ─────────────────────────────────────────────────────────────


def season_json(si: SeasonInfo, locale: str, i18n: I18nCatalog) -> dict:
    return {
        "season": id_label(si.season_id, season_tag(si.season_id), locale, i18n),
        "orbital_position": si.orbital_position,
        "near_event": (
            id_label(si.near_event_id, event_tag(si.near_event_id), locale, i18n)
            if si.near_event_id
            else None
        ),
    }


# ── Sky scene, /sky and /ephemeris (scribal) ────────────────────────────────


def _body_in_scene_tag(b: BodyInScene) -> str:
    if b.body_type == "comet":
        return f"comet.{b.id}"
    if b.body_type == "spark":
        return "body.spark"
    return f"body.{b.id}"


def body_in_scene_json(b: BodyInScene, locale: str, i18n: I18nCatalog) -> dict:
    """direction/color/phase are already locale-baked strings (scene.py bakes
    them in at SkyScene composition time) — pass through as-is, no re-resolve."""
    return {
        "name": id_label(b.id, _body_in_scene_tag(b), locale, i18n),
        "body_type": b.body_type,
        "direction": b.direction,
        "altitude": b.altitude,
        "color": b.color,
        "brightness": b.brightness,
        "phase": b.phase,
    }


def star_in_scene_json(s: StarInScene, locale: str, i18n: I18nCatalog) -> dict:
    """StarInScene.direction is always raw English config text (never
    resolved at composition time, unlike BodyInScene) — the HTML template
    bypasses it and re-resolves star.<id>.position directly; mirrored here."""
    return {
        "name": id_label(s.id, f"star.{s.id}", locale, i18n),
        "position": resolve(f"star.{s.id}.position", locale, i18n),
    }


def house_ref_json(h: HouseRef, locale: str, i18n: I18nCatalog) -> dict:
    return id_label(h.id, f"house.{h.id}", locale, i18n)


def cofullness_tonight_json(
    cf: CofullnessTonightRef | None, locale: str, i18n: I18nCatalog
) -> dict | None:
    if cf is None:
        return None
    return {
        "count": cf.count,
        "moons": [body_name_json(m, locale, i18n) for m in cf.moons],
        "observable": cf.observable,
    }


def next_cofullness_json(
    nev: NextCofullnessRef, locale: str, i18n: I18nCatalog
) -> dict:
    return {
        "pulse": nev.pulse,
        "count": nev.count,
        "moons": [body_name_json(m, locale, i18n) for m in nev.moons],
    }


def scene_json(scene: SkyScene, locale: str, i18n: I18nCatalog) -> dict:
    return {
        "bodies_up": [body_in_scene_json(b, locale, i18n) for b in scene.bodies_up],
        "stars_up": [star_in_scene_json(s, locale, i18n) for s in scene.stars_up],
        "active_house": house_ref_json(scene.active_house, locale, i18n),
        "circumpolar_houses": [
            house_ref_json(h, locale, i18n) for h in scene.circumpolar_houses
        ],
        "co_fullness_tonight": cofullness_tonight_json(
            scene.co_fullness_tonight, locale, i18n
        ),
        "next_co_fullness": next_cofullness_json(scene.next_co_fullness, locale, i18n),
    }


# ── Ephemeris series, /ephemeris ────────────────────────────────────────────
#
# Deliberately a second serialization of EphemerisSeries, not a call into
# render_scribal_json/render_kinematic_json: those two return an intentionally
# locale-invariant flat export string (their own docstrings — "no Fatunik,
# Terpin, or lore terms"), the stable contract /ephemeris/download already
# ships. This one honors DD-0026's per-endpoint localization/{id,label}
# contract instead, over the SAME already-computed EphemerisSeries (get_sky_
# series now takes an optional locale, threaded by the caller — no
# recomputation, no engine behavior change for any existing caller).


def ephemeris_scribal_json(
    series: EphemerisSeries, cfg: AppConfig, locale: str, i18n: I18nCatalog
) -> dict:
    ppd = cfg.time_constants.pulses_per_day

    # EphemerisSeries.day_contexts/steps key astro_day 0-indexed internally
    # (aday = pulse // ppd, see ephemeris.py) — +1 here to match the 1-indexed
    # Astro Day convention every other field in this response (and every
    # other endpoint) uses, so "astro_day" means the same thing everywhere
    # in the JSON contract.
    days: dict[str, dict] = {}
    for aday in sorted(series.day_contexts):
        ctx = series.day_contexts[aday]
        days[str(aday + 1)] = {
            "season": id_label(ctx.season_id, season_tag(ctx.season_id), locale, i18n),
            "body_rise_transit_set": {
                bid: {"rise": rts["rise"], "transit": rts["transit"], "set": rts["set"]}
                for bid, rts in ctx.body_rts.items()
            },
        }

    steps = []
    for step in series.steps:
        scene = step.scene
        steps.append(
            {
                "pulse": step.pulse,
                "astro_day": step.astro_day + 1,
                "astro_time": format_civil_time(step.pulse % ppd, ppd),
                "bodies_up": [
                    body_in_scene_json(b, locale, i18n) for b in scene.bodies_up
                ],
                "stars_up": [
                    star_in_scene_json(s, locale, i18n) for s in scene.stars_up
                ],
                "active_house": house_ref_json(scene.active_house, locale, i18n),
                "circumpolar_houses": [
                    house_ref_json(h, locale, i18n) for h in scene.circumpolar_houses
                ],
                "co_fullness_tonight": cofullness_tonight_json(
                    scene.co_fullness_tonight, locale, i18n
                ),
            }
        )

    return {"days": days, "steps": steps}


def ephemeris_kinematic_json(series: EphemerisSeries, cfg: AppConfig) -> dict:
    """Compact per-body alt/az/illumination/above-horizon for tracked bodies.

    Body ids are dict keys (schema, invariant) — never localized, same as
    every other id in this module.
    """
    tracked = list(cfg.ephemeris.tracked_bodies)

    steps = []
    for step in series.steps:
        sky_map = {sp.name.lower(): sp for sp in step.sky_positions}
        ill_map = {bs.name.lower(): bs.illuminated_fraction for bs in step.body_states}

        bodies: dict[str, dict] = {}
        for body_id in tracked:
            sp = sky_map.get(body_id)
            if sp is None:
                continue
            bodies[body_id] = {
                "alt": round(sp.altitude_deg, 4),
                "az": round(sp.azimuth_deg, 4),
                "ill": round(ill_map.get(body_id, 0.0), 4),
                "up": sp.above_horizon,
            }
        steps.append({"pulse": step.pulse, "bodies": bodies})

    return {"tracked_bodies": tracked, "steps": steps}


def ephemeris_json(
    *,
    series: EphemerisSeries,
    cfg: AppConfig,
    locale: str,
    i18n: I18nCatalog,
    profile: str,
    start_pulse: int,
    end_pulse: int,
) -> dict:
    """Complete /ephemeris response: parameters, summary, and the per-step
    series as a structured object (never a bare top-level array)."""
    return {
        "parameters": {
            "start": temporal_json(start_pulse, cfg, locale),
            "end": temporal_json(end_pulse, cfg, locale),
            "step_pulses": series.step_pulses,
            "step_minutes": series.step_pulses // 60,
            "profile": profile,
        },
        "summary": {
            "step_count": len(series.steps),
            "start_pulse": series.start_pulse,
            "end_pulse": series.end_pulse,
        },
        "series": {
            "scribal": (
                ephemeris_scribal_json(series, cfg, locale, i18n)
                if profile in ("scribal", "both")
                else None
            ),
            "kinematic": (
                ephemeris_kinematic_json(series, cfg)
                if profile in ("kinematic", "both")
                else None
            ),
        },
    }


# ── Error envelope ───────────────────────────────────────────────────────────


def error_json(code: str, message: str) -> dict:
    """Consistent JSON error envelope (DD-0026): stable code + localized text."""
    return {"error": {"code": code, "message": message}}
