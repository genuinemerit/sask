"""Sky-scene composition and text rendering (SPEC-013, SPEC-036).

get_sky_scene(pulse, config, locale=...):
  Composes the full sky scene from existing engine surfaces:
  - season from SPEC-004; bodies above the horizon from SPEC-007/008;
  - visible comets and Spark from SPEC-011;
  - visible fixed stars and active House from SPEC-010;
  - co-fullness tonight and next from SPEC-012.
  locale is threaded here (not just into the render_* functions below)
  because BodyInScene.direction/phase are computed AT COMPOSITION TIME,
  not render time -- see the SPEC-036 devlog entry for why this differs
  from render_lore_date()'s narrower locale-parameterization.

render_night_summary(scene, config, locale=...):
  Localized plain-prose description of the scene. Decomposed into
  whole-sentence catalog templates (DD-0022/SPEC-036) rather than
  translated as opaque strings, since the original composed the summary
  via runtime conditional branching, list-joining, and English
  pluralization -- not simple tag substitution.

render_image_prompt(scene, config, style_id=None):
  Night summary with the selected style's directives appended, always in
  English -- the whole thing is a tool instruction meant to be pasted into
  an AI image generator, not user-facing prose (DD-0022 origin boundary),
  so unlike render_night_summary() its output never follows the page's
  locale. Recomposes its own English-locale scene rather than reusing the
  caller's `scene` as-is, since BodyInScene.direction/color/phase may have
  been baked in at a different locale at get_sky_scene() composition time.
  No AI or network call is made; output is text only.
"""

from __future__ import annotations

from sask.calendar.apparitions import get_apparitions
from sask.calendar.bodies import all_body_states
from sask.calendar.lunar import (
    DEFAULT_COFULLNESS_HORIZON_DAYS,
    get_cofullness,
    next_cofullness,
)
from sask.calendar.season import season_info
from sask.calendar.sky import all_sky_positions
from sask.calendar.stars import get_star_context
from sask.config_loader import AppConfig, I18nCatalog
from sask.i18n.catalog import resolve
from sask.message import (
    BodyInScene,
    BodyState,
    CofullnessTonightRef,
    HouseRef,
    NextCofullnessRef,
    SkyPosition,
    SkyScene,
    StarInScene,
)

_COMPASS_TAGS = [
    "compass.n",
    "compass.ne",
    "compass.e",
    "compass.se",
    "compass.s",
    "compass.sw",
    "compass.w",
    "compass.nw",
]

_SEASON_MOOD_TAGS: dict[str, str] = {
    "greening": "scene.mood.greening",
    "blazing": "scene.mood.blazing",
    "withering": "scene.mood.withering",
    "stillness": "scene.mood.stillness",
}

_PHASE_TAGS = (
    (0.0625, "phase.new"),
    (0.1875, "phase.waxing_crescent"),
    (0.3125, "phase.first_quarter"),
    (0.4375, "phase.waxing_gibbous"),
    (0.5625, "phase.full"),
    (0.6875, "phase.waning_gibbous"),
    (0.8125, "phase.last_quarter"),
)


def _direction_label(
    altitude_deg: float, azimuth_deg: float, locale: str, i18n: I18nCatalog
) -> str:
    """Compass direction plus altitude band from horizontal coordinates."""
    compass_idx = int((azimuth_deg + 22.5) / 45.0) % 8
    compass = resolve(_COMPASS_TAGS[compass_idx], locale, i18n)
    if altitude_deg < 20.0:
        height_tag = "scene.height.low"
    elif altitude_deg < 55.0:
        height_tag = "scene.height.mid"
    else:
        height_tag = "scene.height.high"
    return f"{compass} {resolve(height_tag, locale, i18n)}"


def _phase_label(synodic_frac: float, locale: str, i18n: I18nCatalog) -> str:
    """Named lunar phase from synodic fraction [0, 1), lowercase (scene.py's
    own prose style, vs. translator.py's Title Case for table cells)."""
    if synodic_frac >= 0.9375 or synodic_frac < _PHASE_TAGS[0][0]:
        return resolve("phase.new", locale, i18n).lower()
    for threshold, tag in _PHASE_TAGS[1:]:
        if synodic_frac < threshold:
            return resolve(tag, locale, i18n).lower()
    return resolve("phase.waning_crescent", locale, i18n).lower()


def get_sky_scene(
    pulse: int,
    config: AppConfig,
    *,
    body_states: tuple[BodyState, ...] | None = None,
    sky_positions: tuple[SkyPosition, ...] | None = None,
    locale: str = "en-US",
) -> SkyScene:
    """Compose the full sky scene for the given pulse.

    body_states/sky_positions are computed internally if omitted. A caller
    that already has them for this exact pulse (e.g. get_sky_series, which
    also needs them for the kinematic ephemeris renderer) can pass them in
    to avoid recomputing - the result is identical either way.

    locale defaults to the base locale (SPEC-036) and only affects
    BodyInScene.direction/phase, which -- unlike name/id -- are pre-
    formatted display strings computed here at composition time, not
    resolved later at render time.
    """
    i18n = config.i18n
    si = season_info(pulse, config)

    if body_states is None:
        body_states = all_body_states(pulse, config)
    if sky_positions is None:
        sky_positions = all_sky_positions(pulse, body_states, config)
    sky_pos_map = {sp.name: sp for sp in sky_positions}
    body_cfg_map = {b.name: b for b in config.bodies}

    bodies_up: list[BodyInScene] = []

    # Moons and planets above the horizon and visually detectable (SPEC-007/008)
    for bs in body_states:
        sp = sky_pos_map[bs.name]
        if not sp.above_horizon or not bs.is_visible:
            continue
        bodies_up.append(
            BodyInScene(
                id=bs.name.lower(),
                name=bs.name,
                body_type=bs.body_type,
                direction=_direction_label(
                    sp.altitude_deg, sp.azimuth_deg, locale, i18n
                ),
                altitude=sp.altitude_deg,
                color=resolve(f"body.{bs.name.lower()}.color", locale, i18n),
                brightness=body_cfg_map[bs.name].albedo * bs.illuminated_fraction,
                phase=_phase_label(bs.synodic_fraction, locale, i18n),
            )
        )

    # Visible comets (SPEC-011) — no orbital position available; altitude is nominal
    app = get_apparitions(pulse, config)
    for comet_info in app.comets_visible:
        bodies_up.append(
            BodyInScene(
                id=comet_info.id,
                name=comet_info.name,
                body_type="comet",
                direction=resolve("scene.direction_above_horizon", locale, i18n),
                altitude=45.0,
                color=resolve(f"comet.{comet_info.id}.color", locale, i18n),
                brightness=comet_info.visibility,
                phase=resolve("scene.phase_tail_visible", locale, i18n),
            )
        )

    # Spark (SPEC-011) — shown near its host moon if that moon is above the horizon
    if app.spark.visible:
        host_body = next(
            (
                b
                for b in config.bodies
                if b.name.lower() == config.spark.host_moon.lower()
            ),
            None,
        )
        if host_body and sky_pos_map[host_body.name].above_horizon:
            sp = sky_pos_map[host_body.name]
            direction = _direction_label(sp.altitude_deg, sp.azimuth_deg, locale, i18n)
            altitude = sp.altitude_deg
        else:
            direction = resolve("scene.direction_above_horizon", locale, i18n)
            altitude = 45.0
        bodies_up.append(
            BodyInScene(
                id=config.spark.id,
                name="the Spark",
                body_type="spark",
                direction=direction,
                altitude=altitude,
                color=resolve("body.spark.color", locale, i18n),
                brightness=app.spark.visibility,
                phase=resolve("scene.phase_glimpsed", locale, i18n),
            )
        )

    # Stars and houses (SPEC-010)
    sc = get_star_context(pulse, config)
    star_cfg_map = {s.id: s for s in config.stars}
    stars_up = tuple(
        StarInScene(
            id=fs.id,
            name=fs.name,
            direction=star_cfg_map[fs.id].position,
        )
        for fs in sc.visible_fixed_stars
    )
    active_house = HouseRef(
        id=sc.house_of_the_equinox.id,
        name=sc.house_of_the_equinox.name,
    )
    circumpolar_houses = tuple(
        HouseRef(id=h.id, name=h.name) for h in sc.circumpolar_houses
    )

    # Co-fullness this Astro day and next (SPEC-012)
    ppd = config.time_constants.pulses_per_day
    today_midnight = (pulse // ppd) * ppd

    tonight_events = get_cofullness(today_midnight, today_midnight + ppd - 1, config)
    co_fullness_tonight: CofullnessTonightRef | None = None
    if tonight_events:
        ev = tonight_events[0]
        # Observable if any near-full moon is already above the horizon or will
        # rise before the end of the current Astro day. Illumination changes
        # slowly enough that a moon near-full at midnight remains near-full at rise.
        observable = any(
            sky_pos_map[mid.capitalize()].above_horizon
            or (
                sky_pos_map[mid.capitalize()].rise_pulse is not None
                and sky_pos_map[mid.capitalize()].rise_pulse < today_midnight + ppd
            )
            for mid in ev.moons
        )
        co_fullness_tonight = CofullnessTonightRef(
            count=ev.count, moons=ev.moons, observable=observable
        )

    next_start = today_midnight + ppd
    nev = next_cofullness(next_start, config)
    if nev is not None:
        next_cofullness_ref = NextCofullnessRef(
            pulse=nev.pulse, count=nev.count, moons=nev.moons
        )
    else:
        # Sentinel: no co-fullness found within the horizon
        next_cofullness_ref = NextCofullnessRef(
            pulse=next_start + DEFAULT_COFULLNESS_HORIZON_DAYS * ppd,
            count=0,
            moons=(),
        )

    return SkyScene(
        pulse=pulse,
        season=si.season_id,
        bodies_up=tuple(bodies_up),
        stars_up=stars_up,
        active_house=active_house,
        circumpolar_houses=circumpolar_houses,
        co_fullness_tonight=co_fullness_tonight,
        next_co_fullness=next_cofullness_ref,
    )


def render_night_summary(
    scene: SkyScene, config: AppConfig, locale: str = "en-US"
) -> str:
    """Localized plain-prose description of the sky scene (DD-0022, SPEC-036).

    Decomposed into whole-sentence catalog templates with placeholders --
    the original composed this via runtime conditional branching, list-
    joining, and English-only pluralization, none of which survive as
    simple tag substitution. Body/star/house display names resolve via
    their stable .id fields (the same catalog tags already used
    elsewhere), never via the locale-neutral .name field.
    """
    i18n = config.i18n
    lines: list[str] = []

    mood_tag = _SEASON_MOOD_TAGS.get(scene.season)
    if mood_tag:
        lines.append(resolve(mood_tag, locale, i18n))
    else:
        lines.append(
            resolve("scene.unknown_season", locale, i18n).replace(
                "{season}", scene.season
            )
        )

    moons = [b for b in scene.bodies_up if b.body_type == "moon"]
    if moons:
        descs = [
            f"{resolve(f'body.{b.id}', locale, i18n)} ({b.color}, {b.phase}) {b.direction}"
            for b in moons
        ]
        lines.append(
            resolve("scene.moons_line", locale, i18n).replace(
                "{list}", "; ".join(descs)
            )
        )
    else:
        lines.append(resolve("scene.no_moons_line", locale, i18n))

    planets = [b for b in scene.bodies_up if b.body_type == "planet"]
    if planets:
        descs = [
            f"{resolve(f'body.{b.id}', locale, i18n)} ({b.color}) {b.direction}"
            for b in planets
        ]
        lines.append(
            resolve("scene.wanderers_line", locale, i18n).replace(
                "{list}", "; ".join(descs)
            )
        )

    for c in [b for b in scene.bodies_up if b.body_type == "comet"]:
        lines.append(
            resolve("scene.comet_line", locale, i18n)
            .replace("{name}", resolve(f"comet.{c.id}", locale, i18n))
            .replace("{color}", c.color)
        )

    for s in [b for b in scene.bodies_up if b.body_type == "spark"]:
        lines.append(
            resolve("scene.spark_line", locale, i18n).replace(
                "{direction}", s.direction
            )
        )

    house_name = resolve(f"house.{scene.active_house.id}", locale, i18n)
    house_line = resolve("scene.house_line", locale, i18n).replace(
        "{house}", house_name
    )
    n = len(scene.stars_up)
    if n:
        star_list = ", ".join(
            resolve(f"star.{s.id}", locale, i18n) for s in scene.stars_up[:3]
        )
        if n > 3:
            more = n - 3
            other_tag = (
                "scene.and_other_singular" if more == 1 else "scene.and_other_plural"
            )
            star_list += " " + resolve(other_tag, locale, i18n).replace(
                "{more}", str(more)
            )
        count_tag = "scene.star_count_singular" if n == 1 else "scene.star_count_plural"
        house_line += " " + resolve(count_tag, locale, i18n).replace(
            "{n}", str(n)
        ).replace("{list}", star_list)
    lines.append(house_line)

    if scene.co_fullness_tonight:
        moon_names = ", ".join(
            resolve(f"body.{m}", locale, i18n) for m in scene.co_fullness_tonight.moons
        )
        c = scene.co_fullness_tonight.count
        obs = (
            ""
            if scene.co_fullness_tonight.observable
            else resolve("scene.obs_below_horizon", locale, i18n)
        )
        cf_tag = "scene.cofullness_singular" if c == 1 else "scene.cofullness_plural"
        lines.append(
            resolve(cf_tag, locale, i18n)
            .replace("{c}", str(c))
            .replace("{names}", moon_names)
            .replace("{obs}", obs)
        )

    ppd = config.time_constants.pulses_per_day
    days = max(0, (scene.next_co_fullness.pulse - scene.pulse + ppd - 1) // ppd)
    next_cf_tag = (
        "scene.next_cofullness_singular"
        if days == 1
        else "scene.next_cofullness_plural"
    )
    lines.append(resolve(next_cf_tag, locale, i18n).replace("{days}", str(days)))

    return " ".join(lines)


def render_image_prompt(
    scene: SkyScene,
    config: AppConfig,
    style_id: str | None = None,
) -> str:
    """Night summary with the selected style's image-generation directives appended.

    Always English (DD-0022 origin boundary: a tool instruction meant to be
    pasted into an AI image generator, not user-facing prose) -- recomposes
    its own English-locale scene rather than trusting the caller's `scene`,
    since BodyInScene.direction/color/phase may have been baked in at a
    different locale at get_sky_scene() composition time.
    No AI or network call is made. Output is deterministic text only.
    """
    effective_id = (
        style_id if style_id is not None else config.sky_style_settings.default_style
    )
    style = next(s for s in config.sky_styles if s.id == effective_id)

    en_scene = get_sky_scene(scene.pulse, config, locale="en-US")
    summary = render_night_summary(en_scene, config, "en-US")

    directives = [style.medium, style.palette, style.composition]
    if style.extra:
        directives.append(style.extra)

    return f"{summary}\n\nImage style: {'. '.join(directives)}."
