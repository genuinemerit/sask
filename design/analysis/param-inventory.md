# Parameter inventory (SPEC-041)

Read directly from `src/sask/web/routes.py` (and `src/sask/web/__init__.py` for
the two globally-handled params) ahead of designing `config/endpoint_params.toml`.
This is the behavior contract the SPEC-041 refactor must reproduce exactly,
except where the owner explicitly approved a change (noted inline).

Path note: SPEC-041's own text names this file `analysis/param-inventory.md`,
but the codebase's established convention for this kind of writeup is
`design/analysis/*.md` (see `design/analysis/debt-0005-coverage-triage.md`,
DEBT-0005's own inventory). No top-level `analysis/` directory exists in the
repo. Filed here instead, following the existing convention rather than the
SPEC's literal (imprecise) path — the same category of drafting note
SPEC-040 flags about itself.

## Global params (handled outside per-route parsing — not touched)

| Param | Where handled | Behavior |
|---|---|---|
| `format` | `routes.py:_wants_json()` (73-81) | `format=json` (case-insensitive) forces JSON; any other value or absence falls through to `Accept` header negotiation. |
| `locale` | `web/__init__.py:_bind_locale` (81-90) | If it names a locale in `cfg.i18n.locales`, wins and is persisted to a cookie; otherwise silently falls through to the cookie, then `Accept-Language`, then the catalog base locale. Never errors on a bad value. |

Both are implicitly accepted on every one of the five endpoints below, and are
excluded from strict unknown-param rejection (SPEC-041) without being repeated
in each endpoint's declared param set.

## `/` (`index`, routes.py:283-320)

| Param | Type | Required | Default | Constraint | Error (bad value) |
|---|---|---|---|---|---|
| `pulse` | number (parsed `round(float(x))`) | optional | none — no pulse means an empty form (HTML) / `error.missing_moment_query` (JSON) | must parse as float | `error.invalid_pulse_value` |

No `astro_day`/`time_of_day`/fatunik/terpin support on this route — asymmetric
vs. `/moons`, `/planets`, `/sky` below. This is existing, deployed behavior,
preserved exactly (not "fixed" — out of scope per DD-0028).

## `/moons`, `/planets`, `/sky` (routes.py:323-606, all three call `_resolve_pulse`, 106-176)

Full moment resolution, priority order — first populated branch wins:

| Priority | Branch | Fields | Error (bad value) |
|---|---|---|---|
| 1 | pulse | `pulse` — `int(round(float(x)))` | `error.invalid_pulse_value` |
| 2 | astro_day | `astro_day` (int) + optional `time_of_day` (string, `HH:MM:SS`) | `error.invalid_astro_day` (bad `astro_day`); `error.invalid_time_of_day` (bad `time_of_day`, via `CalendarRangeError` from `resolve_moment`) |
| 3 | fatunik_date | `fatunik_year`, `fatunik_month`, `fatunik_day` (all int, all three required together) | `error.invalid_fatunik_date` |
| 4 | terpin_date | `terpin_year`, `terpin_month`, `terpin_day` (all int, all three required together) | `error.invalid_terpin_date` |

If none of the four branches has input: HTML renders the empty form; JSON
returns `error.missing_moment_query` (400).

## `/ephemeris` (routes.py:609-792)

**Start** — identical full moment resolution to the above, **prefixed**
`start_` (`_resolve_endpoint("start_", ...)`, routes.py:179-271), same four
branches/priority, using the `error.invalid_prefixed_*` tag family instead
(`error.invalid_prefixed_pulse`, `error.invalid_prefixed_astro_day`,
`error.invalid_prefixed_time_of_day`, `error.invalid_prefixed_fatunik_date`,
`error.invalid_prefixed_terpin_date`) — each message additionally carries the
literal prefix.

**End** — NOT a full moment group. Only two inputs are accepted:

| Param | Type | Notes |
|---|---|---|
| `end_pulse` | number (`int(round(float(x)))`) | Presence selects "pulse mode." |
| `duration_days` | int, `>= 1` | Presence (when `end_pulse` absent) selects "date mode": `end_pulse = start_pulse + duration_days * ppd`. |

**Other params:**

| Param | Type | Required | Default | Constraint |
|---|---|---|---|---|
| `step_minutes` | int (`step_pulses = int(x) * 60`) | required whenever any ephemeris field is submitted | none | — |
| `profile` | string | optional | `"scribal"` | **Today: none** — any value accepted; unrecognized values silently produce `null` for both `series.scribal` and `series.kinematic`. **Owner-approved change (this round):** becomes an enum `{scribal, kinematic, both}`; an invalid value now 400s with a new `error.invalid_profile` tag, matching `/ephemeris/download`'s existing (separate, out-of-scope) stricter behavior. |

**Cross-field sequencing** (any_input = any of start/end_pulse/duration_days/step_minutes present):

1. `start_pulse` missing → `error.start_time_required`
2. `step_minutes` missing → `error.step_required`; malformed → `error.invalid_step_minutes`
3. Pulse mode (`end_pulse` present) and malformed → `error.invalid_prefixed_pulse` (prefix `end_`, reused from the moment-group tag family even though end isn't a full moment group)
4. Pulse mode and `end_pulse` still `None` after parse → `error.end_pulse_required`
5. Date mode: `duration_days` missing → `error.duration_required`; malformed → `error.invalid_duration_days`; `< 1` → `error.duration_min`
6. Once `end_pulse` and `step_pulses` both resolved: `step_pulses >= (end_pulse - start_pulse)` → `error.step_exceeds_duration`
7. Absolute throttle (step floor / range cap), enforced in `calendar/ephemeris.py:_validate_throttle` from `cfg.ephemeris.step_floor_pulses` / `cfg.ephemeris.range_cap_pulses` (untouched, out of scope) → `error.ephemeris_range_invalid`
8. If `any_input` is false: JSON → `error.missing_ephemeris_query`; HTML → empty form.

This sequencing is genuine per-endpoint business logic (mode selection +
required-field cascade), not a static per-param constraint — it stays as
route orchestration code in the refactor, built from the shared helper's
typed/validated values rather than raw strings.

## `/ephemeris/download` (routes.py:795-847) — NOT one of DD-0028's five endpoints

Separate, unprefixed param shape (`start`, `end`, `step` via `request.args[...]`,
`KeyError`/`ValueError` → plain-text 400, not the JSON envelope; `profile`
restricted to exactly `{"scribal", "kinematic"}`, no `"both"`). Left untouched.

## Owner decisions applied in this round

- **Unknown/misspelled query params**: today silently ignored on all five
  endpoints (confirmed: no code path rejects them). This round switches to
  **strict rejection** (`error.unknown_param`, 400) — a deliberate behavior
  change the owner approved, since the audience integrating against these
  endpoints values a typo pointed out over silent wrong behavior. Confirmed
  against all current param-bearing tests (`tests/test_spec_005/009/014/016/
  019/035/036/037/039.py`): none send a param outside the sets documented
  above, so no existing test regresses.
- **`/ephemeris`'s `profile`**: see above — becomes a validated enum, a
  deliberate behavior change the owner approved for consistency with
  `/ephemeris/download`'s existing stricter behavior.

No other inconsistency was found across the five endpoints' current handling.
