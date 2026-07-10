# Legacy i18n Deepening Analysis (SPEC-035)

Deepens [port-feature-analysis.md](port-feature-analysis.md) and
[port-design-components-analysis.md](port-design-components-analysis.md)'s
first-pass survey of `saskan-app-alt`'s i18n system, specifically through
`sask`'s clean-room lens (DD-0022). **Recommend-only — ports no code.**
Source, re-read fresh in full for this analysis:
`saskan-app-alt/saskan/infra/i18n/{lookup.py,localize.py}`,
`saskan-app-alt/saskan/data/locales/{en-US,es-ES}/messages.yaml`,
`saskan-app-alt/saskan/data/locales/i18n_keymap.json`,
`saskan-app-alt/docs/architecture/i18n_authoring_guide.md`,
`saskan-app-alt/docs/architecture/adr/{0010-services-metadata,0014-startup-handshake-activation}.md`,
`saskan-app-alt/tests/test_lookup.py`,
`saskan-app-alt/saskan/infra/config/services.py`.

## Fallback chain: adopt the shape, not the rung count

Legacy's `lookup.get_text()` implements a 4-rung chain: active locale bundle
→ en-US bundle → caller-supplied `fallback` string → the raw `i18n_id`
itself. `sask`'s target (per DD-0022) is 3 rungs: locale → base (en-US) →
raw key. **The caller-supplied-fallback rung does not port** — it exists in
legacy because `get_text()` is called from many different sites each
wanting a different default; `sask`'s resolver has a single, uniform
contract (`resolve(tag, locale, catalog) -> str`) with no per-call-site
fallback override, so that rung would add a parameter nothing in the new
design needs. `sask`'s resolver: locale hit → base-locale hit → raw tag
string, using explicit `dict.get(tag)` / `is None` checks at each step —
not Python truthiness (see bug below).

## Format: TOML, resolving the legacy inconsistency explicitly

Legacy's own `i18n_authoring_guide.md` states locale files are JSON; the
actual shipped `messages.yaml` files are YAML — the guide and the code
disagree with each other. `sask` avoids importing this inconsistency by
using **TOML** throughout (`config/i18n/en-US.toml`, `es-ES.toml`), matching
every other `sask` config file and the existing `tomllib`-based loading
convention in `config_loader.py`. This isn't a compromise between legacy's
two conflicting claims — it's a third, deliberate choice consistent with
`sask`'s own convention.

## Bugs found — confirmed not to repeat

1. **`fallback or i18n_id` truthiness bug** (`lookup.py`, the final
   fallback line). Because Python treats an empty string as falsy, a
   caller intentionally passing `fallback=""` (meaning "show nothing if
   untranslatable") silently collapses into "show the raw id instead" —
   the exact opposite of what was intended. Confirmed live in
   `localize.py::format_reply()`, which calls `get_text(value,
   fallback="")` for every payload value: because of this bug, combined
   with reason-code enum values (e.g. `protocol_version_unsupported`)
   never actually being present in `messages.yaml`, end users see raw
   snake_case internal codes printed verbatim in CLI output, in both
   locales. **`sask`'s resolver must use explicit `None`-checks at each
   fallback rung, never `or`/truthiness**, so an intentionally-empty
   catalog value is never confused with an absent one.
2. **Bare `except Exception`** around bundle loading in `lookup.py`
   (`_load_bundle`) and keymap loading in `localize.py` (`_load_keymap`).
   Any error — malformed file, permissions, packaging misconfiguration —
   is silently swallowed and converted into a fallback/empty dict, making
   misconfiguration hard to detect. **`sask` does not repeat this**: catalog
   *loading* errors (a malformed TOML file, a duplicate tag key) go through
   `config_loader.py`'s existing `_require()`/`ConfigError` fail-fast idiom,
   exactly like every other config concern — this is a different failure
   mode from DD-0022's silent-fallback rule, which covers content
   *absence* at *resolve* time, not structural errors at *load* time. A
   malformed catalog file should be a loud `ConfigError` naming the file,
   not a silent empty catalog.
3. **`log.*` namespace documented but never shipped.** The authoring
   guide and `convert_tag()`'s docstring both describe a `log.*` namespace;
   it appears in neither locale file. A minor doc/reality drift, alongside
   the JSON/YAML one — not itself a reason to adopt or avoid anything, just
   evidence that legacy's docs and shipped data drifted apart more than
   once.
4. **`i18n_keymap.json`'s `convert_tag()` applied uniformly to dict keys
   AND values** (`localize.py::format_reply`), even though the keymap is
   documented and structured only for field *names*. This works today only
   by accident — non-string/non-matching values silently no-op through the
   membership check. Not a pattern worth reusing at all (see two-tier
   assessment below).

## Locale selection: the one genuine architectural gap

Legacy's `lang()` reads `os.getenv("SASKAN_LANG", ...)` **fresh on every
call**, coerced against `SUPPORTED_LANGS`, with no per-request or
per-connection context anywhere. `get_text()` does accept an explicit
`locale:` override parameter, but grepping the entire legacy codebase for
call sites shows it is **never actually used** — every real call defers to
the global `lang()`.

This "works" in legacy only because of where localization actually happens
architecturally: the server (`infra/net/server/server.py`) never localizes
anything itself — it ships raw i18n **tags** over the wire as-is (e.g.
`motd=svc.MOTD` is literally the string `"ui.message_of_the_day"`, not
resolved text). Localization happens exactly once, client-side, in a
single-user, single-process CLI invocation (`localize.py::format_reply()`,
called from `ui_cli/commands/connect.py`). A CLI invocation is inherently
one process handling one locale — the global-env-var approach never has to
arbitrate between two different locales at once, so its unsafety never
surfaces.

**This is the single most important thing `sask` must not copy.** `sask`'s
Flask web adapter renders localized HTML **server-side, per request, inside
a multi-threaded/multi-worker process** — precisely the situation legacy's
architecture was designed to avoid ever needing to handle. If `sask`'s
resolver read a global/env-var locale the way `lang()` does, one request's
bound locale could leak into a concurrently-handled request's response.
`sask`'s resolver must take locale as an **explicit argument**, passed by
whichever adapter (web `before_request` hook, CLI root callback) bound it
for that specific request/invocation — never ambient global state. This is
also why legacy's unused `locale:` override parameter is worth noting: it's
the *shape* of the right idea (explicit locale, not global), just never
actually wired end-to-end in legacy. `sask` wires it end-to-end from day
one.

## Two-tier design: keep the concept, not the implementation

Legacy splits into `lookup.py` (generic key→string resolution, no
domain knowledge) and `localize.py` (a keymap-based translation of
internal dict field names into i18n tags, `format_reply()`). The
separation of concerns — generic lookup vs. a small, domain-specific
id→tag mapping — is worth keeping as a *concept*: `sask`'s
`src/sask/i18n/catalog.py` plays the `lookup.py` role, and a small
`src/sask/i18n/tags.py` (plus `translator.py`'s own existing lookup
tables) play the `localize.py` role. But legacy's actual
`format_reply()` implementation — walking an arbitrary reply dict and
applying the same `convert_tag()` to every key *and* value — is
over-fit to one specific wire-protocol shape and fragile (see bug 4
above). `sask` does not port `format_reply`'s dict-walking logic; the
id→tag mappings it needs (e.g. `season_tag(season_id)`) are small,
explicit, typed functions, not a generic dict-sweep.

## Naming convention: adopt the shape, not the vocabulary

Legacy's dotted-lowercase-segment tag convention (`system.welcome`,
`ui.label.x`, enforced by regex in the authoring guide) is a clean,
mechanically-checkable pattern worth adopting as-is. The specific
namespace *vocabulary* legacy uses (`system`/`msg`/`ui`/`err`/`log`) is
entirely shaped by its game-protocol/handshake domain and has no bearing
on `sask`'s content — `sask` defines its own vocabulary
(`nav.*`/`label.*`/`sentence.*`/`season.*`/etc.) from its own content
shapes, per the content inventory.

One structural note for `sask`'s own TOML authoring: legacy's YAML files
are flat maps whose keys merely *contain* literal dots (`err.connection_refused:
"..."`), never genuine nested YAML structure. TOML natively supports real
nested tables (`[err]` / `connection_refused = "..."`), which legacy never
explored. `sask` deliberately keeps the flat-dotted-key shape (one `[tags]`
table per locale file) rather than nesting — this keeps the validator's
completeness check a plain set-difference, with no recursive table
walking.

## Caching: the pattern is sound, but sask likely needs none of it

Legacy's `@lru_cache` on `_load_bundle()`/`_load_keymap()` is a safe,
correct use of caching — locale files are static package data, never
written at runtime, and `lru_cache` is internally thread-safe. But `sask`'s
own config-loading convention already loads everything exactly once, at
`load_config()` time, into an immutable `AppConfig` held for the life of
the process (web) or the invocation (CLI) — the "load once" property
`lru_cache` buys legacy is already free in `sask`'s architecture. **No
separate cache layer is needed** for the i18n catalog; it's just another
field on `AppConfig`, loaded once like everything else.

## Parallel-document / whole-prose translation: confirmed absent in legacy

Every legacy i18n artifact examined — both locale files (18 short,
single-sentence-or-shorter lines each), the keymap, the authoring guide,
ADR-0014's embedded i18n section — describes and implements only short,
individually-tagged strings, resolved one key at a time. There is no
concept anywhere of translating a whole document or article as a unit.
`sask`'s parallel-document mechanism for help pages (DD-0022) is wholly new
design, not adapted from legacy.

## Recommendation summary

| Legacy mechanic | Adopt for sask? |
|---|---|
| 3-4 rung fallback chain shape | Yes, at 3 rungs (locale → base → raw tag); drop the caller-fallback rung |
| JSON-vs-YAML format | No — sask uses TOML, resolving legacy's own internal inconsistency |
| `fallback or i18n_id` truthiness | No — explicit `None`-checks at each fallback step |
| Bare `except Exception` in loaders | No — reuse `config_loader.py`'s `_require()`/`ConfigError` fail-fast idiom for load errors (distinct from content-absence fallback) |
| Global `os.getenv()` locale selection | **No — the one genuine anti-pattern.** sask's resolver takes locale as an explicit argument; sask's web adapter localizes per-request in a concurrent process, unlike legacy's server |
| Two-tier lookup/domain-mapping separation | Yes, as a concept (`catalog.py` + small `tags.py`/`translator.py` mappings) |
| `format_reply()`'s blanket key+value dict-sweep | No — too fragile/over-fit; sask uses small explicit typed mapping functions |
| Dotted-lowercase namespace convention | Yes, as a mechanical pattern; sask defines its own vocabulary |
| `@lru_cache` per-locale-bundle | No separate cache needed — sask's `AppConfig` already loads once |
| Parallel-document translation | N/A — doesn't exist in legacy; wholly new to sask |
