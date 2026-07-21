# i18n Content Inventory (SPEC-035)

Inventories every user-facing string in `sask`'s current web surface,
tiered by content shape, per DD-0022's origin-based scope (localize what
the user reads; logs/diagnostics/relayed operator content are excluded).
**Recommend-only — this document is the target list for the future
bulk-translation follow-on; only a small canary slice is actually
translated this round.**

## Method

Read every template (`base.html` + all 7 page templates), `routes.py`'s
hardcoded validation/error strings, `translator.py`'s display-formatting
functions, `scene.py`/`lore.py`'s engine-level text-producing functions,
and confirmed the 3 help documents' existence/size.

## Tier counts

| Tier | Approx. count | Where |
|---|---|---|
| LABEL | ~140 | nav links, page titles, headings, fieldset legends, form labels, buttons, table headers (~55 across 5 data tables), Yes/No, brightness-band words, `translator.py`'s 8-way phase-name and 16-way compass tables |
| SENTENCE | ~30 | `routes.py` validation/error f-strings (~20), template empty-states (3), season line, help "not found" message |
| STATEMENT | ~2-3 | `ephemeris.html`'s instructional paragraph (4 static sentences, no conditionals); `help/index.md`'s short intro |
| COMPOSED-PROSE | 2 core cases (+2 borderline template-level) | `scene.py::render_night_summary()`/`render_image_prompt()`; borderline: `planets.html`'s "Through a glass" fragment assembly, `sky.html`'s in-template co-fullness pluralization |
| PARALLEL-DOCUMENT | 3 files, 264 lines | `docs/help/{index,getting-started,calendar-lore}.md` |

## LABEL tier — representative examples

- `base.html`: 6 nav links ("Pulse", "Moons", "Planets", "Sky",
  "Ephemeris", "Help"); the single `<html lang="en">` hardcode (line 2 —
  the only locale-adjacent markup anywhere in the templates).
- Every page: title block, `<h1>`, fieldset legends ("Enter pulse", "Or
  Astro day", "Or Fatunik date", "Or Terpin date"), field labels ("Pulse",
  "Year", "Month", "Day"), "Query"/"Generate"/"Reset" buttons.
- Table headers: 12 in `moons.html`, 11 in `planets.html`, ~8 each across
  `sky.html`'s 5 sub-tables (calendars, moons, wanderers, comets, stars).
- `sky.html`: brightness-band words ("Brilliant", "Bright", "Moderate",
  "Faint", "Dim") appear as literal English words in **two separate
  places** (moons-up and planets-up tables) — worth deduplicating into one
  shared lookup when this is bulk-translated, not just tagged twice.
- `translator.py`: `_phase_name` (8-way moon-phase lookup: New, Waxing
  Crescent, First Quarter, ...), `_CARDINAL` (16-way compass abbreviation
  table), eclipse type capitalization ("Solar"/"Lunar"/"—"). All uniformly
  1:1 lookup tables — see the tag-vs-identifier resolution below.

## SENTENCE tier — representative examples

All of `routes.py`'s validation messages are simple f-strings with data
slots, no English-specific branching — e.g. `f"Invalid pulse value:
{pulse_param!r} — enter a number."`, `"Duration (Days) must be at least
1."`, `f"Step ({step_min} min) equals or exceeds the total duration
({span_min} min) — reduce Step or increase Duration (Days))."`. One caveat
worth a follow-on flag (not fixed this round): several error paths surface
a raw Python exception message directly (`f"Invalid Fatunik date: {exc}"`,
`str(exc)` from `get_sky_series`) — these need their own audit later to
confirm the underlying exception text is itself simple enough to tag, or
needs replacing with a dedicated sask-authored message.

## STATEMENT tier

`ephemeris.html`'s instructional paragraph (4 sentences, fully static, no
conditionals) is the clean example — straightforward multi-sentence block,
substitutable as one tag with no internal structure.

## COMPOSED-PROSE — the required flag

**`src/sask/calendar/scene.py::render_night_summary()`/`render_image_prompt()`
are genuinely composed prose, not simple tag substitution.** Confirmed by
direct read: the function builds a variable-length list of English
sentences via real conditional branching, list-joining, and **runtime
English pluralization/agreement logic**:

- Conditional branch + list-join: `if moons: lines.append("Moons above the
  horizon: " + "; ".join(descs) + ".")` vs. `else: "No moons are above the
  horizon."`
- Same pattern for planets, plus a per-body loop for comets/sparks
  (0..N sentences).
- Real English number agreement computed at runtime: `noun = "stars" if n
  != 1 else "star"`, `verb = "are" if n != 1 else "is"`, an "and N others"
  truncation idiom for star lists beyond 3.
- Co-fullness sentences: `f"{c} moon{'s' if c != 1 else ''} are near-full
  together..."` — the same singular/plural ternary pattern, duplicated a
  second time for "next co-fullness."

**This cannot be localized by swapping string constants.** Proper
localization requires decomposing it into structured data (already mostly
available as `SkyScene` fields — `bodies_up`, `active_house`, `stars_up`,
`co_fullness_tonight`, `next_co_fullness`) plus locale-aware templates with
real plural/list-formatting rules (e.g. Jinja `{% trans %}`/`ngettext`-style
pluralization, since English's singular/plural binary doesn't generalize —
many languages have different plural-count rules or none at all).
**Recommendation: flag as a follow-on, do not decompose in this round** —
matches DD-0022's own deferred scope and SPEC-035's explicit "not all done
in SPEC-035" framing. `render_image_prompt()` inherits this problem
entirely (it wraps `render_night_summary()` and appends one simple,
already-externalized config-driven directive list).

**Contrast case — the pattern to grow toward:**
`src/sask/calendar/lore.py::render_lore_date()`/`render_lore_time()` are
**already good tag-substitution examples**: they do `.replace("{token}",
value)` over format strings that are themselves externalized *config
data* (`lore.format_str`, authored in `lore_time.toml`/`*_solar.toml`),
not Python string literals. The only branching is *which* format
string/token set to use (solar vs. lunar, era mode) — data-driven
dispatch, not sentence construction. One small, contained wrinkle: the
embedded `_ordinal()` helper hardcodes English 1st/2nd/3rd suffix rules —
would need a locale-aware equivalent if any lore format string renders an
ordinal in a non-English context. Flagged, not fixed this round.

**Borderline, template-level cases worth noting for the bulk-translation
follow-on:**
- `planets.html`'s "Through a glass" detail row assembles mutually-exclusive
  English sentence fragments via nested Jinja `{% if %}` — same character
  as the composed-prose problem, just in the template rather than Python.
- `sky.html`'s co-fullness block duplicates the `'s' if count != 1 else
  ''` pluralization ternary directly in Jinja, separately from `scene.py`'s
  own copy of the same logic for a different sentence — both need the same
  eventual ICU-plural treatment.

## The tag-vs-identifier sub-decision — resolved

DD-0022 explicitly defers the choice between "engine emits i18n tags
directly" and "engine emits domain identifiers that a thin render-layer
maps to tags," pending this inventory. The answer is not a single global
choice — it depends on content shape, exactly as expected:

- **`src/sask/web/translator.py`** already sits precisely at the adapter
  render boundary (it converts locale-agnostic engine message units —
  `BodyState`, `SkyPosition`, `PulseInfo` — into display-ready ViewModels)
  and its lookup tables are uniformly 1:1: 8 phase names, 16 compass
  points, never context-dependent on the caller. **Resolution: the engine
  already emits domain identifiers (raw synodic-fraction floats, raw
  azimuth degrees) — `translator.py` is the thin render-layer DD-0022
  anticipates, extended to map identifier → i18n tag, handing the tag to
  the new resolver.**
- **`src/sask/calendar/season.py::season_info()`** returns a `SeasonInfo`
  message unit whose `season_id` field is a clean, stable 4-value enum
  (`greening|blazing|withering|stillness`) — uniformly 1:1 mappable to
  `season.<id>` tags. This is the canary's chosen "localized engine
  result" (see porting-roadmap/porting plan for the concrete wiring).
- **`scene.py`'s composed prose** is the one case where there is no 1:1
  id→tag mapping at all — it's not identifier-to-tag, it's
  structured-data-to-template. This is exactly why the sub-decision has no
  single global answer: it's resolved per content shape, and this
  inventory's job was to show which shape each piece of content actually
  has, not to force one mechanism onto all of them.

## Addendum (SPEC-036) — scholar-description classification: templated, not LLM-generated

SPEC-036's `dynamic_content` deliverable requires resolving whether the
"in-game scholar" night-sky description (`scene.py::render_night_summary()`/
`render_image_prompt()`) is TEMPLATED assembly or LLM-GENERATED, since the
two classifications imply different localization mechanisms (decompose into
template+tags, vs. make locale a generation parameter).

**Confirmed by direct read of `scene.py` (module docstring and both function
docstrings): TEMPLATED ASSEMBLY.** No AI or network call is made anywhere in
either function — output is deterministic Python string-building over
`SkyScene` data (conditional branches, list-joins, runtime plural/agreement
ternaries), exactly as this document's COMPOSED-PROSE section above already
described. There is no LLM call to parameterize with locale; the
`render_image_prompt()` output is text handed to an *external* AI
image-generator as an instruction, not generated *by* one.

This confirms the COMPOSED-PROSE section's standing recommendation now
applies as SPEC-036's actual scope (no longer deferred): decompose into
structured data (already available as `SkyScene` fields) plus locale-aware
templates with explicit en-US/es-ES plural/agreement handling (general
ICU-style plural machinery remains deferred — only the two languages in
scope need explicit rules). `render_image_prompt()`'s own directive list
stays English/system-facing (a tool instruction, not user-facing prose) per
DD-0022's origin boundary — only the `render_night_summary()` portion it
wraps is user-facing and needs localization.

## Help documents — confirmed for the parallel-document mechanism

`docs/help/index.md` (6 lines, 271 bytes), `getting-started.md` (50
lines, 2168 bytes), `calendar-lore.md` (208 lines, 9902 bytes) — all
confirmed appropriate for whole-document translation (DD-0022's parallel-
document mechanism), given their length and prose density; none are
candidates for fragment-level tagging. **`getting-started.md` is the
canary's pick** — shortest non-trivial document, giving a real but
small translation task.

## Locale-adjacent markup — exhaustive

Confirmed by repo-wide grep: exactly one `lang=` occurrence anywhere in
the templates (`base.html:2`, `<html lang="en">`), and zero existing
`locale`/`i18n`/`gettext`/`babel` references anywhere in `src/sask/`. There
is no other `hreflang`, `dir`, or `<meta http-equiv="content-language">`
markup to account for.

## Follow-on (explicitly not done this round)

The full ~170 LABEL+SENTENCE strings and 2-3 STATEMENT blocks catalogued
here are the target list for a future bulk-translation SPEC, once this
round's canary machinery (catalog, resolver, parallel-doc selection,
validator, locale selection on both adapters) is proven. This round
translates only: the canary's handful of `nav.*`/`season.*` tags, the
`/sky` season display, and one help document
(`getting-started.es-ES.md`).
