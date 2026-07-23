"""Sky-scene ephemeris: time-series generation and JSON renderers (SPEC-015).

get_sky_series(start_pulse, end_pulse, step_pulses, config):
  Validates throttle constraints and builds a time-series of sky scenes over
  [start_pulse, end_pulse] at the given step. Per-day context (season,
  rise/transit/set) is computed once per distinct Astro day.

render_scribal_json(series, config):
  Readable per-step record: pulse, Astro day, time-of-day, bodies, stars,
  house, co-fullness, prose summary. No civil/lore terms.

render_kinematic_json(series, config):
  Compact per-body alt/az, illumination, and above-horizon flag for every
  tracked body at each step, including below-horizon positions.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

from sask.calendar.bodies import all_body_states
from sask.calendar.pulse import format_civil_time
from sask.calendar.scene import get_sky_scene, render_night_summary
from sask.calendar.season import season_info
from sask.calendar.sky import all_sky_positions
from sask.config_loader import AppConfig
from sask.logsetup import get_logger
from sask.message import BodyState, SkyPosition, SkyScene

logger = get_logger(__name__)

# DD-0020 level_rubric: WARNING when a request nears/exceeds the ~5s soft
# ephemeris budget (REQ-OPS-010 upper bound; tools/ops/perf_config.py
# BUDGETS["ephemeris_worst_case_s"] = (3.0, 5.0)).
_EPHEMERIS_NEAR_BUDGET_S = 4.5


# ── Internal series data structures ───────────────────────────────────────────


@dataclass
class _DayCtx:
    """Per-Astro-day context computed once for all steps in that day."""

    season_id: str
    season_name: str
    # body_id (lowercase) → {rise, transit, set} pulse values
    body_rts: dict[str, dict[str, int | None]]


@dataclass
class _Step:
    """One step in the ephemeris series.

    body_states/sky_positions are the same per-pulse data already folded
    into scene (via get_sky_scene); stored here too so render_kinematic_json
    can reuse them instead of recomputing all_body_states/all_sky_positions.
    """

    pulse: int
    astro_day: int
    scene: SkyScene
    body_states: tuple[BodyState, ...]
    sky_positions: tuple[SkyPosition, ...]


@dataclass
class EphemerisSeries:
    """Complete series data returned by get_sky_series."""

    start_pulse: int
    end_pulse: int
    step_pulses: int
    day_contexts: dict[int, _DayCtx]  # astro_day → context
    steps: list[_Step]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _validate_throttle(
    start_pulse: int,
    end_pulse: int,
    step_pulses: int,
    config: AppConfig,
) -> None:
    eph = config.ephemeris
    if step_pulses < eph.step_floor_pulses:
        raise ValueError(
            f"step_pulses {step_pulses} is below the minimum of "
            f"{eph.step_floor_pulses} pulses (5 minutes)"
        )
    span = end_pulse - start_pulse
    if span < 0:
        raise ValueError(f"end_pulse {end_pulse} is before start_pulse {start_pulse}")
    if span > eph.range_cap_pulses:
        raise ValueError(
            f"range of {span} pulses exceeds the maximum of "
            f"{eph.range_cap_pulses} pulses (30 days)"
        )


# ── Public API ────────────────────────────────────────────────────────────────


def get_sky_series(
    start_pulse: int,
    end_pulse: int,
    step_pulses: int,
    config: AppConfig,
) -> EphemerisSeries:
    """Validate throttle and build the ephemeris series.

    Raises ValueError if step_pulses < step_floor_pulses or
    (end_pulse - start_pulse) > range_cap_pulses.

    Per-day context (season, body rise/transit/set) is computed once per
    distinct Astro day and referenced by all steps within that day.
    """
    _validate_throttle(start_pulse, end_pulse, step_pulses, config)
    started = time.perf_counter()

    ppd = config.time_constants.pulses_per_day
    day_contexts: dict[int, _DayCtx] = {}
    steps: list[_Step] = []

    for pulse in range(start_pulse, end_pulse + 1, step_pulses):
        aday = pulse // ppd
        step_body_states = all_body_states(pulse, config)
        step_sky_positions = all_sky_positions(pulse, step_body_states, config)
        scene = get_sky_scene(
            pulse,
            config,
            body_states=step_body_states,
            sky_positions=step_sky_positions,
        )

        if aday not in day_contexts:
            day_start = aday * ppd
            si = season_info(day_start, config)
            day_body_states = all_body_states(day_start, config)
            day_sky_pos = all_sky_positions(day_start, day_body_states, config)
            body_rts: dict[str, dict[str, int | None]] = {
                sp.name.lower(): {
                    "rise": sp.rise_pulse,
                    "transit": sp.transit_pulse,
                    "set": sp.set_pulse,
                }
                for sp in day_sky_pos
            }
            day_contexts[aday] = _DayCtx(
                season_id=si.season_id,
                season_name=si.name,
                body_rts=body_rts,
            )

        steps.append(
            _Step(
                pulse=pulse,
                astro_day=aday,
                scene=scene,
                body_states=step_body_states,
                sky_positions=step_sky_positions,
            )
        )

    duration_s = time.perf_counter() - started
    log_fields = {
        "step_count": len(steps),
        "duration_s": round(duration_s, 3),
    }
    if duration_s >= _EPHEMERIS_NEAR_BUDGET_S:
        logger.warning("ephemeris request completed", extra=log_fields)
    else:
        logger.info("ephemeris request completed", extra=log_fields)

    return EphemerisSeries(
        start_pulse=start_pulse,
        end_pulse=end_pulse,
        step_pulses=step_pulses,
        day_contexts=day_contexts,
        steps=steps,
    )


def render_scribal_json(
    series: EphemerisSeries, config: AppConfig, locale: str = "en-US"
) -> str:
    """Render the scribal profile: a readable per-step record.

    No Fatunik, Terpin, or lore terms appear in the output. locale only
    affects the "summary" field (SPEC-036, wraps render_night_summary) --
    every other field (season_name, body direction/phase, etc.) is a
    stable data-export value, deliberately out of SPEC-036's scope.
    """
    ppd = config.time_constants.pulses_per_day

    days_obj: dict[str, dict] = {}
    for aday in sorted(series.day_contexts):
        ctx = series.day_contexts[aday]
        days_obj[str(aday)] = {
            "season_id": ctx.season_id,
            "season_name": ctx.season_name,
            "body_rise_transit_set": {
                bid: {
                    "rise": rts["rise"],
                    "transit": rts["transit"],
                    "set": rts["set"],
                }
                for bid, rts in ctx.body_rts.items()
            },
        }

    steps_list: list[dict] = []
    for step in series.steps:
        scene = step.scene
        co_full = None
        if scene.co_fullness_tonight is not None:
            cf = scene.co_fullness_tonight
            co_full = {
                "count": cf.count,
                "moons": list(cf.moons),
                "observable": cf.observable,
            }
        steps_list.append(
            {
                "pulse": step.pulse,
                "astro_day": step.astro_day,
                "time_of_day": format_civil_time(step.pulse % ppd, ppd),
                "bodies_up": [
                    {
                        "id": b.id,
                        "name": b.name,
                        "body_type": b.body_type,
                        "direction": b.direction,
                        "altitude": round(b.altitude, 4),
                        "color": b.color,
                        "brightness": round(b.brightness, 6),
                        "phase": b.phase,
                    }
                    for b in scene.bodies_up
                ],
                "stars_up": [
                    {"id": s.id, "name": s.name, "direction": s.direction}
                    for s in scene.stars_up
                ],
                "active_house": {
                    "id": scene.active_house.id,
                    "name": scene.active_house.name,
                },
                "circumpolar_houses": [
                    {"id": h.id, "name": h.name} for h in scene.circumpolar_houses
                ],
                "co_fullness_tonight": co_full,
                "summary": render_night_summary(scene, config, locale),
            }
        )

    return json.dumps(
        {
            "profile": "scribal",
            "start_pulse": series.start_pulse,
            "end_pulse": series.end_pulse,
            "step_pulses": series.step_pulses,
            "step_count": len(series.steps),
            "days": days_obj,
            "steps": steps_list,
        },
        indent=2,
    )


def render_kinematic_json(series: EphemerisSeries, config: AppConfig) -> str:
    """Render the kinematic profile: compact per-body alt/az for all tracked bodies.

    Includes below-horizon bodies (negative altitude, up=False) for smooth arcs.
    No Fatunik, Terpin, or lore terms appear in the output.
    """
    tracked = list(config.ephemeris.tracked_bodies)

    steps_list: list[dict] = []
    for step in series.steps:
        sky_map = {sp.name.lower(): sp for sp in step.sky_positions}
        ill_map = {bs.name.lower(): bs.illuminated_fraction for bs in step.body_states}

        bodies_obj: dict[str, dict] = {}
        for body_id in tracked:
            sp = sky_map.get(body_id)
            if sp is None:
                continue
            bodies_obj[body_id] = {
                "alt": round(sp.altitude_deg, 4),
                "az": round(sp.azimuth_deg, 4),
                "ill": round(ill_map.get(body_id, 0.0), 4),
                "up": sp.above_horizon,
            }

        steps_list.append({"pulse": step.pulse, "bodies": bodies_obj})

    return json.dumps(
        {
            "profile": "kinematic",
            "start_pulse": series.start_pulse,
            "end_pulse": series.end_pulse,
            "step_pulses": series.step_pulses,
            "step_count": len(series.steps),
            "tracked_bodies": tracked,
            "steps": steps_list,
        },
        indent=2,
    )
