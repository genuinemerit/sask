"""SPEC-017/SPEC-036: lore overlay renderers for time-of-day and calendar dates.

Locale is threaded as an explicit argument (DD-0022): the engine positions
(month/day/age/quarter index) are computed here as before, but the displayed
VOCABULARY and the format TEMPLATE itself are resolved from the shared i18n
catalog per locale, not read directly off CalendarLoreConfig's English
fields. Those fields remain the config-loading structural/validation source
(counts, indices, era mode); the catalog is authoritative for display text.
"""

from __future__ import annotations

from sask.calendar.lunar import _synodic_period_days, get_lunar_date
from sask.calendar.pulse import astro_to_fatunik, astro_to_terpin
from sask.config_loader import AppConfig, CalendarLoreConfig, I18nCatalog, LoreAge
from sask.i18n.catalog import resolve
from sask.message import CalendarDate, LunarDate


def _ordinal_en(n: int) -> str:
    """Return English ordinal string (1 -> '1st', 6 -> '6th')."""
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    r = n % 10
    suffix = ("st", "nd", "rd")
    return f"{n}{suffix[r - 1] if 1 <= r <= 3 else 'th'}"


def _ordinal_es(n: int, feminine: bool = False) -> str:
    """Spanish ordinal marker (e.g. '3.º' / '3.ª'), the standard
    numeral + degree-sign convention (avoids needing spelled-out irregular
    ordinal words beyond ~10)."""
    return f"{n}.ª" if feminine else f"{n}.º"


def _ordinal(n: int, locale: str, feminine: bool = False) -> str:
    if locale == "es-ES":
        return _ordinal_es(n, feminine)
    return _ordinal_en(n)


def _tag_or_empty(value: str | None, tag: str, locale: str, i18n: I18nCatalog) -> str:
    """Resolve tag unless the source config field is None (field absent for
    this calendar shape, e.g. week_word on a phase-week calendar)."""
    if value is None:
        return ""
    return resolve(tag, locale, i18n)


def _find_age_idx(ages: tuple[LoreAge, ...], turn: int) -> int:
    """Return the 0-based index into ages of the applicable age for turn."""
    result = 0
    for i in range(1, len(ages)):
        if ages[i].start_turn <= turn:
            result = i
    return result


def _month_name(
    lore: CalendarLoreConfig, month_idx: int, locale: str, i18n: I18nCatalog
) -> str:
    if lore.festival_index is not None and month_idx == lore.festival_index:
        return resolve(f"lore.{lore.id}.festival_name", locale, i18n)
    if lore.month_names is None:
        return str(month_idx)
    position = (
        month_idx if lore.festival_index is None else month_idx - lore.festival_index
    )
    return resolve(f"lore.{lore.id}.month.n{position}", locale, i18n)


def _phase_idx(day: int, cycle_days: float, n_phases: int) -> int:
    """Return 0-based phase index for a 1-based day within a lunation cycle."""
    return min(int((day - 1) * n_phases / cycle_days), n_phases - 1)


def render_lore_time(pulse: int, culture: str, config: AppConfig, locale: str) -> str:
    """Render pulse as a localized lore watch/shur/keyt string for the culture."""
    lore = config.lore_time
    cult = next((c for c in lore.cultures if c.name == culture), None)
    if cult is None:
        raise ValueError(f"Unknown lore culture: {culture!r}")

    day_start = cult.day_start_pulses
    t = ((pulse % 86400) - day_start) % 86400
    shur_idx = t // 7200
    keyt_idx = (t % 7200) // 720
    watch_idx = shur_idx // 2

    watch_name = resolve(f"lore.time.watch.n{watch_idx + 1}", locale, config.i18n)
    template = resolve("lore.time.format", locale, config.i18n)
    return (
        template.replace("{watch}", watch_name)
        .replace("{shur}", str(shur_idx + 1))
        .replace("{keyt}", str(keyt_idx + 1))
    )


def render_lore_date(
    technical_date: CalendarDate | LunarDate,
    calendar_id: str,
    config: AppConfig,
    locale: str,
) -> str:
    """Render a CalendarDate or LunarDate as a localized full lore date string."""
    lore = next((c for c in config.lore_calendars if c.id == calendar_id), None)
    if lore is None:
        raise ValueError(f"Unknown lore calendar: {calendar_id!r}")

    if lore.kind == "solar":
        assert isinstance(technical_date, CalendarDate)
        return _render_solar(technical_date, lore, locale, config.i18n)
    assert isinstance(technical_date, LunarDate)
    return _render_lunar(technical_date, lore, config, locale)


def _render_solar(
    date: CalendarDate, lore: CalendarLoreConfig, locale: str, i18n: I18nCatalog
) -> str:
    assert lore.ages is not None
    assert lore.week_length is not None
    assert lore.day_names is not None

    age_idx = _find_age_idx(lore.ages, date.year)
    month_name = _month_name(lore, date.month, locale, i18n)
    week_idx = (date.day - 1) // lore.week_length
    day_in_week = (date.day - 1) % lore.week_length

    day_name = resolve(f"lore.{lore.id}.day.n{day_in_week + 1}", locale, i18n)
    week_word = _tag_or_empty(lore.week_word, f"lore.{lore.id}.week_word", locale, i18n)
    turn_word = _tag_or_empty(lore.turn_word, f"lore.{lore.id}.turn_word", locale, i18n)
    age_name = resolve(f"lore.{lore.id}.age.n{age_idx + 1}", locale, i18n)
    template = resolve(f"lore.{lore.id}.format_full", locale, i18n)

    return (
        template.replace("{day_name}", day_name)
        .replace("{week_ordinal}", _ordinal(week_idx + 1, locale))
        .replace("{week_word}", week_word)
        .replace("{month}", month_name)
        .replace("{turn_word}", turn_word)
        .replace("{turn}", str(date.year))
        .replace("{age}", age_name)
    )


def _render_lunar(
    date: LunarDate, lore: CalendarLoreConfig, config: AppConfig, locale: str
) -> str:
    i18n = config.i18n
    cal_cfg = next(c for c in config.lunar_calendars if c.id == lore.id)
    cycle_days = _synodic_period_days(cal_cfg.moon, config)

    if lore.era_mode == "none":
        assert lore.phase_terms is not None
        phase_idx = _phase_idx(date.day, cycle_days, len(lore.phase_terms))
        phase_term = resolve(f"lore.{lore.id}.phase.n{phase_idx + 1}", locale, i18n)
        moon_word = _tag_or_empty(
            lore.moon_word, f"lore.{lore.id}.moon_word", locale, i18n
        )
        template = resolve(f"lore.{lore.id}.format_full", locale, i18n)
        return (
            template.replace("{phase_term}", phase_term)
            .replace("{day}", _ordinal(date.day, locale))
            .replace("{moon_word}", moon_word)
            .replace(
                "{moon_count}",
                _ordinal(date.lunation + 1, locale, feminine=(locale == "es-ES")),
            )
        )

    assert date.has_turns
    assert lore.quarter_names is not None
    month_name = _month_name(lore, date.month, locale, i18n)  # type: ignore[arg-type]
    quarter_idx = _phase_idx(date.day, cycle_days, len(lore.quarter_names))
    quarter = resolve(f"lore.{lore.id}.quarter.n{quarter_idx + 1}", locale, i18n)
    turn_word = _tag_or_empty(lore.turn_word, f"lore.{lore.id}.turn_word", locale, i18n)
    template = resolve(f"lore.{lore.id}.format_full", locale, i18n)

    if lore.era_mode == "round":
        round_word = _tag_or_empty(
            lore.round_word, f"lore.{lore.id}.round_word", locale, i18n
        )
        return (
            template.replace("{quarter}", quarter)
            .replace("{day}", str(date.day))
            .replace("{month}", month_name)
            .replace("{turn_word}", turn_word)
            .replace("{short}", str(date.short_count))  # type: ignore[union-attr]
            .replace("{round_word}", round_word)
            .replace("{long}", str(date.long_count + 1))  # type: ignore[operator]
        )

    # era_mode == "ages"
    assert lore.ages is not None
    age_idx = _find_age_idx(lore.ages, date.turn)  # type: ignore[arg-type]
    age_name = resolve(f"lore.{lore.id}.age.n{age_idx + 1}", locale, i18n)
    return (
        template.replace("{quarter}", quarter)
        .replace("{day}", str(date.day))
        .replace("{month}", month_name)
        .replace("{turn_word}", turn_word)
        .replace("{turn}", str(date.turn))  # type: ignore[union-attr]
        .replace("{age}", age_name)
    )


def apply_lore_overlay(
    scribal_record: dict,
    culture: str,
    calendar_id: str,
    config: AppConfig,
    locale: str,
) -> dict:
    """Return a copy of scribal_record with lore_time and lore_date added.

    Does not mutate the original dict.
    """
    pulse = scribal_record["pulse"]
    lore_cfg = next((c for c in config.lore_calendars if c.id == calendar_id), None)
    if lore_cfg is None:
        raise ValueError(f"Unknown lore calendar: {calendar_id!r}")

    if lore_cfg.kind == "solar":
        tech_date: CalendarDate | LunarDate = (
            astro_to_fatunik(pulse, config)
            if calendar_id == "fatunik_solar"
            else astro_to_terpin(pulse, config)
        )
    else:
        tech_date = get_lunar_date(pulse, calendar_id, config)

    result = dict(scribal_record)
    result["lore_time"] = render_lore_time(pulse, culture, config, locale)
    result["lore_date"] = render_lore_date(tech_date, calendar_id, config, locale)
    return result
