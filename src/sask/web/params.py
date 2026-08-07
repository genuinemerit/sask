"""Shared query-param parse/validate helper, driven by the DD-0028/SPEC-041
single-source declaration (config/endpoint_params.toml, loaded into
AppConfig.endpoint_params).

Flask-free (takes a param mapping, not `request` directly) — same discipline
as api/json_render.py — so it can be exercised directly in tests without a
request context.

resolve_moment_group() reproduces the exact branch-priority logic the old
per-route `_resolve_pulse`/`_resolve_endpoint` functions implemented (see
design/analysis/param-inventory.md), parameterized by the declaration's field
names/prefix instead of hardcoding them per call site — the two functions
collapse into this one. The branch -> error-tag mapping is NOT derivable by a
uniform naming rule (the unprefixed pulse branch is irregularly named
"invalid_pulse_value", not "invalid_pulse" — every other branch's unprefixed/
prefixed pair differs only by the "prefixed_" infix), so it is kept as
explicit data here rather than guessed at.

parse_scalar() and check_params() are new, generic pieces: the former
centralizes type coercion per the declaration's `type` field (constraint
checks like duration_days' "must be >= 1" stay as explicit route code reading
`spec.constraints["min"]` — see routes.py — since which failure produces
which error tag is genuinely bespoke per param, not a pattern worth forcing
into one generic shape); the latter is the new strict unknown-param
rejection plus format/locale value enforcement (both owner-approved
behavior changes — see SPEC-041's devlog entries).
"""

from __future__ import annotations

from collections.abc import Mapping

from sask.calendar.pulse import (
    CalendarRangeError,
    fatunik_to_pulse,
    terpin_to_pulse,
)
from sask.calendar.pulse import resolve_moment as resolve_astro_moment
from sask.i18n.catalog import resolve as resolve_i18n
from sask.message import CalendarDate

from ..config_loader import (
    AppConfig,
    EndpointParamSpec,
    EndpointParamsConfig,
    I18nCatalog,
    MomentGroupSpec,
    ParamSpec,
)

_MOMENT_ERROR_TAGS: dict[str, dict[str, str]] = {
    "pulse": {
        "unprefixed": "error.invalid_pulse_value",
        "prefixed": "error.invalid_prefixed_pulse",
    },
    "astro_day": {
        "unprefixed": "error.invalid_astro_day",
        "prefixed": "error.invalid_prefixed_astro_day",
    },
    "time_of_day": {
        "unprefixed": "error.invalid_time_of_day",
        "prefixed": "error.invalid_prefixed_time_of_day",
    },
    "fatunik_date": {
        "unprefixed": "error.invalid_fatunik_date",
        "prefixed": "error.invalid_prefixed_fatunik_date",
    },
    "terpin_date": {
        "unprefixed": "error.invalid_terpin_date",
        "prefixed": "error.invalid_prefixed_terpin_date",
    },
}


def msg(tag: str, locale: str, i18n: I18nCatalog, **kwargs: str) -> str:
    """Resolve tag and substitute {key} placeholders from kwargs (SPEC-036)."""
    text = resolve_i18n(tag, locale, i18n)
    for key, value in kwargs.items():
        text = text.replace(f"{{{key}}}", value)
    return text


def err(tag: str, locale: str, i18n: I18nCatalog, **kwargs: str) -> tuple[str, str]:
    """Resolve tag to (code, localized message) for an error response.

    code is the tag's stable, English, locale-invariant suffix — shared by
    the HTML path (which only needs the message) and the JSON error envelope
    (DD-0026), which needs the code too.
    """
    return tag.removeprefix("error."), msg(tag, locale, i18n, **kwargs)


def resolve_moment_group(
    args: Mapping[str, str],
    group: MomentGroupSpec,
    cfg: AppConfig,
    locale: str,
    prefix: str = "",
) -> tuple[int | None, str | None, str | None]:
    """Resolve a moment-group param set to a pulse integer, or an error.

    Priority: as declared in group.priority (first populated branch wins).
    Returns (pulse, None, None) on success; (None, code, msg) on bad input;
    (None, None, None) when no branch had any input.
    """
    i18n = cfg.i18n
    ppd = cfg.time_constants.pulses_per_day
    kind = "prefixed" if prefix else "unprefixed"

    def _tag_kwargs(**extra: str) -> dict[str, str]:
        if prefix:
            extra["prefix"] = prefix
        return extra

    for branch in group.priority:
        fields = group.fields[branch]

        if branch == "pulse":
            (pulse_name,) = fields
            raw = args.get(f"{prefix}{pulse_name}") or None
            if raw is None:
                continue
            try:
                return int(round(float(raw))), None, None
            except ValueError:
                tag = _MOMENT_ERROR_TAGS["pulse"][kind]
                code, message = err(tag, locale, i18n, **_tag_kwargs(value=repr(raw)))
                return None, code, message

        elif branch == "astro_day":
            day_name, tod_name = fields
            raw = args.get(f"{prefix}{day_name}") or None
            if raw is None:
                continue
            tod_raw = args.get(f"{prefix}{tod_name}") or None
            try:
                day = int(raw)
            except ValueError:
                tag = _MOMENT_ERROR_TAGS["astro_day"][kind]
                code, message = err(tag, locale, i18n, **_tag_kwargs(value=repr(raw)))
                return None, code, message
            try:
                return resolve_astro_moment(day, tod_raw, ppd), None, None
            except CalendarRangeError:
                tag = _MOMENT_ERROR_TAGS["time_of_day"][kind]
                code, message = err(
                    tag, locale, i18n, **_tag_kwargs(value=repr(tod_raw))
                )
                return None, code, message

        elif branch in ("fatunik_date", "terpin_date"):
            y_name, m_name, d_name = fields
            year = args.get(f"{prefix}{y_name}") or None
            month = args.get(f"{prefix}{m_name}") or None
            day_ = args.get(f"{prefix}{d_name}") or None
            if not (year and month and day_):
                continue
            calendar_id = "fatunik" if branch == "fatunik_date" else "terpin"
            converter = (
                fatunik_to_pulse if branch == "fatunik_date" else terpin_to_pulse
            )
            try:
                date = CalendarDate(calendar_id, int(year), int(month), int(day_))
                return converter(date, cfg), None, None
            except (ValueError, KeyError) as exc:
                tag = _MOMENT_ERROR_TAGS[branch][kind]
                code, message = err(tag, locale, i18n, **_tag_kwargs(detail=str(exc)))
                return None, code, message

        else:  # pragma: no cover — declaration validated at load time
            raise AssertionError(f"unknown moment branch {branch!r}")

    return None, None, None


def parse_scalar(raw: str, spec: ParamSpec) -> int | float | str:
    """Coerce raw per spec.type. Raises ValueError on failure (including an
    enum value outside spec.constraints['values']).

    Which error tag a caller maps ValueError to differs per param and even
    per failure mode within one param (e.g. duration_days: malformed int vs.
    below its declared minimum are two different tags) — so tag selection
    stays explicit in the caller (routes.py) rather than being forced into
    one generic shape here.
    """
    if spec.type == "int":
        return int(raw)
    if spec.type == "float":
        return float(raw)
    if spec.type == "enum":
        if raw not in spec.constraints["values"]:
            raise ValueError(raw)
        return raw
    return raw


def known_param_names(
    endpoint: EndpointParamSpec, declaration: EndpointParamsConfig
) -> set[str]:
    """Every query key `endpoint` accepts: its declared scalars, its moment
    group's fields (prefixed), plus the declaration's global params."""
    names = set(declaration.globals)
    names.update(endpoint.scalars)
    if endpoint.moment_group:
        group = declaration.moment_groups[endpoint.moment_group]
        for branch_fields in group.fields.values():
            names.update(f"{endpoint.moment_group_prefix}{f}" for f in branch_fields)
    return names


def check_params(
    args: Mapping[str, str], path: str, cfg: AppConfig, locale: str
) -> tuple[str | None, str | None]:
    """Validate every query key for `path` against the declaration (SPEC-041,
    owner-approved behavior changes):
      - a key not declared for `path` -> error.unknown_param
      - a present `format` value outside its declared enum -> error.invalid_format
      - a present `locale` value outside its declared enum -> error.invalid_locale
    """
    declaration = cfg.endpoint_params
    endpoint = declaration.endpoints[path]
    known = known_param_names(endpoint, declaration)
    for key in args:
        if key not in known:
            return err("error.unknown_param", locale, cfg.i18n, param=key)

    fmt_raw = args.get("format") or None
    if fmt_raw is not None:
        fmt_values = declaration.params["format"].constraints["values"]
        if fmt_raw.lower() not in fmt_values:  # _wants_json() is case-insensitive
            return err("error.invalid_format", locale, cfg.i18n, value=repr(fmt_raw))

    locale_raw = args.get("locale") or None
    if locale_raw is not None:
        locale_values = declaration.params["locale"].constraints["values"]
        if locale_raw not in locale_values:
            return err(
                "error.invalid_locale",
                locale,
                cfg.i18n,
                value=repr(locale_raw),
                values=", ".join(locale_values),
            )

    return None, None
