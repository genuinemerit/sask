# Integration seams — where a port's delineation decisions will live

`sask-calendar` has four shared concerns that any new functional area —
asset-serving included — would have to pass through: config loading, the
message-unit seam, the Flask/Jinja presentation layer, and persistence. This
document walks each one and states, as precisely as the current code
supports, where sask's resource-service code would touch it and what's
unresolved at that touch-point. None of these are resolved here — that's
deliberate; see open-questions.md.

## 1. Config loading

`sask-calendar`'s `config_loader.py` defines one `AppConfig` dataclass tree,
built by `load_config(config_dir: Path) -> AppConfig`, which loads a fixed,
known list of TOML filenames (`time_constants.toml`, `calendars.toml`, ...,
through six `lore_*` calendar-overlay files) and validates each one
exhaustively — exact list lengths, type checks, cross-references like
`default_style` having to name an id that actually exists among the loaded
styles (`config_loader.py:801-805`). The function signature itself
enumerates the contract: add a new config concern, and `load_config()`'s
body and `AppConfig`'s field list both have to grow to know about it.

sask's two loaders (`auth.load_tokens`, `manifest.load_manifest`) have no
equivalent of `AppConfig` to join — they're free-standing functions returning
a list and a dict respectively, invoked from inside a route handler rather
than from an app-factory config-loading step, and validated far more loosely
(no cardinality checks, no cross-reference checks; a malformed manifest entry
missing a required TOML key raises a bare `KeyError` from `manifest.py:56-59`
rather than a typed `ConfigError`).

The seam, concretely: does an asset catalog (and a token store, if one is
built) become a new field on `AppConfig`, loaded once at `create_app()` time
and subject to the same exact-validation discipline as every other config
file — or does it stay a separate, separately-lifecycled concern that
`AppConfig` doesn't know about? Either answer is structurally available
today; neither is implied by anything already built. See open-questions.md
item 2.

## 2. The message-unit seam

`src/sask/message.py`'s docstring states the rule directly: "Downstream
callers (UI, tests) import only from this module — never from internal
engine modules directly." Every engine function (`pulse_info`,
`all_body_states`, `get_sky_scene`, etc.) returns one of the frozen
dataclasses defined there, and `message.py` even ships a `validate()`
function (`message.py:276`) that checks no non-Optional field holds `None` —
a meta-level contract check, not just a type hint. REQ-OPS-008 makes this a
formal requirement: "Every engine function returns a defined message unit
... ad hoc or type-heterogeneous returns are not permitted."

sask's `manifest.ResourceEntry` (`manifest.py:12`) is already a frozen-ish
dataclass with a comparable shape (it's actually mutable — no
`@dataclass(frozen=True)` — unlike every dataclass in `message.py`), but it
was never written against `message.py`'s conventions because no such module
existed in sask's own codebase, and sask's auth/manifest functions return
raw `list[dict]` and `dict[tuple, ResourceEntry]` rather than anything
shaped like a message unit at all.

The seam, concretely: asset lookup isn't a citizen of the message-unit
contract today. For it to become one, an asset-shaped dataclass would need
to live in `message.py` (frozen, snake_case, `validate()`-compatible) and the
lookup logic would need to live in an engine-shaped module that returns that
type — rather than, as in sask, living as inline logic inside the Flask route
itself. DD-0003's "engine never imports Flask" rule means this isn't a style
preference; it's the same boundary that already keeps `pulse.py`/`bodies.py`
free of Flask, applied to whatever asset-lookup function would exist.

## 3. The Flask/Jinja presentation layer

`sask-calendar`'s `web/routes.py` funnels every engine result through
`web/translator.py` into a view-model dataclass (`PulseViewModel`,
`MoonViewModel`, `PlanetViewModel`) before a template ever sees it
(`web/translator.py`'s docstring: "Converts raw engine output into
display-ready strings. No web-layer dependency."). Every route renders an
HTML template for a person looking at a browser; DD-0003 fixes this as
server-rendered, no-JavaScript Jinja, deliberately.

sask's `/resource/<kind>/<resource_id>` is not presentation in this sense at
all — it returns raw bytes or a JSON error directly, addressed to (per the
project's own framing in `docs/notes/lessons.md`) "the client (desktop)
[that] holds a session token" — a program, not a person looking at a page.

The seam, concretely: DD-0003 already anticipated this shape of consumer
without naming it — "The seam is shaped so an HTTP API, and later the RPG
engine, can wrap the same calls without changing the engine (API-ready, not
API-now)." A ported asset service would plug in beside the existing
Jinja routes as its own Blueprint or route group answering bytes/JSON, not
as another HTML page, and — per the same DD-0003 rule that keeps the engine
Flask-free — it could not live inside whatever engine-side module ends up
holding asset-lookup logic. Whether the asset service *is* the
API-ready consumer DD-0003 was leaving room for, or a third kind of
consumer neither DD-0003 nor sask anticipated, is open — see
open-questions.md item 1.

## 4. Persistence

Covered in full in `persistence.md`; the short version for this seam
inventory: this is the one touch-point where `sask-calendar` today has no
existing pattern to extend at all. There is no per-request file I/O, no
cache, no database anywhere in the current engine or web code — config is
loaded once and held in memory for the process's life. Any persistence a
ported asset service brings with it (even just "read this manifest file
again on each request") would be introducing a new kind of I/O into the
app's request path, not joining an established one. That makes this seam
less about reconciling two existing patterns and more about deciding,
without precedent inside this codebase, what the first one should be.
