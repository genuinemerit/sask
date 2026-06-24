# Source inventory — what was reviewed in `sask`'s application layer

All paths below are relative to `~/Code/sask` unless noted. "In scope" means
it directly informs the functional-area picture; "redesign candidate" means
the thing exists and does something real, but its specific shape is a poor
fit for `sask-calendar` and should be rebuilt deliberately rather than copied
— see the dedicated section at the end of this file. "Out" means it was read
only enough to confirm it's deployment-layer or otherwise irrelevant here.

## Application code — `src/sask/`

| File | What it does | Scope |
|---|---|---|
| `app.py` | Flask app factory; `/health` (no auth) and `/resource/<kind>/<resource_id>` (bearer-token auth, three hardcoded kinds) | **In** — the whole request lifecycle lives here; see `functional-architecture.md`. |
| `auth.py` | Loads a flat list of bearer tokens from a TOML file; extracts/validates the `Authorization` header with `hmac.compare_digest` | **In, but the token model is a redesign candidate** — see below. The constant-time comparison itself is a sound, reusable idea independent of the storage shape around it. |
| `manifest.py` | Loads `resources/manifest.toml` into a `dict[(kind, id), ResourceEntry]`; `ResourceEntry` is a plain dataclass (kind, id, path, content_type) | **In, heavily** — the kind/id addressing model and the manifest-as-catalog pattern are the closest thing sask has to an "asset management" concept. |
| `translators.py` | All response-body serialization: JSON encode for health/error, raw byte read for a resource file | **In, pattern only — name is a redesign candidate.** `sask-calendar` already has a module literally named `web/translator.py` doing a different job (message-unit → view-model). See open-questions.md item 7. |
| `__init__.py` | One-line package docstring | Not meaningfully in scope. |

## Resources — `resources/`

| Item | Scope |
|---|---|
| `manifest.toml` | **In** — the entire schema sask uses for a resource catalog: `[[resource]]` entries with `kind`, `id`, `path` (relative to the manifest's own directory), `content_type`. Four entries total. |
| `images/splash.png`, `json/scenario-001.json`, `audio/ambient-loop.mp3`, `audio/ambient-video.mp4` | **In, as evidence of shape, not content.** All four are placeholder files (PR-002 explicitly scoped "real game assets" out). Worth noting `ambient-video.mp4` has `kind = "audio"` but `content_type = "video/mp4"` — kind and content-type are independently configurable in this schema, not derived from one another. |

## Requirements — `requirements/functional.toml`

| ID | Title | Scope |
|---|---|---|
| REQ-FUN-001 | Resource delivery endpoint | **In** — core contract: authenticated GET returns resource bytes; 401/404 behavior specified. |
| REQ-FUN-002 | Resource kinds supported | **In** — names the three kinds (image/json/audio) and their Content-Type expectations as a requirement, not just an implementation detail. |
| REQ-FUN-003 | Service reachable over HTTPS at deployed URL | **Out, mostly** — this is a deployment-acceptance criterion (TLS validity, byte-for-byte match against the live droplet) wearing a "functional" category label. Already substantively covered by `analysis/deployment/` and DD-0014/SPEC-024. |

`requirements/operational.toml`'s REQ-OPS-004 ("App tokens deployed from
developer machine") is **out** here — it's the deployment mechanism for
getting a tokens file onto the droplet, already covered in
`analysis/deployment/source-inventory.md`. Only the fact that app-level
secrets are a distinct category from infra secrets (ADR-0001) matters on the
functional side, and that's covered below.

## Decisions (ADRs) — `decisions/`

| File | Scope |
|---|---|
| `0001-secrets-policy.toml` | **Partly in.** The two-category secrets split itself is deployment-layer (already ported). What's functionally relevant is the *followup* text: "Token rotation requires a redeploy unless we later add sqlite-backed token storage... consider sqlite-backed token store as a future ADR." This was never built — see `persistence.md`. |
| `0002-service-framework-and-conventions.toml` | **Moot to re-litigate.** Decides Flask + explicit translator functions + no Pydantic. `sask-calendar` already independently arrived at a stricter version of the same idea — typed, frozen, `validate()`-checkable message-unit dataclasses (`src/sask/message.py`, REQ-OPS-008) — which is the more developed convention of the two. Nothing here needs porting; `sask-calendar`'s own pattern should govern any new code. |
| `0006-application-secrets-deployment.toml` | **Out** — deployment mechanism (Ansible `copy` + `no_log` + mode 0600), already covered in `analysis/deployment/`. Its *existence* matters only as confirmation that sask anticipated needing this and built it for a token model that, per DD-0014, `sask-calendar` doesn't currently have a use for. |

## PR spec — `prs/0002-local-resource-service.toml`

**In, heavily.** This is the single richest functional-scope document in the
source project. Its `scope.out` list is itself a usable inventory of
deliberately-deferred functional work, none of which was ever picked back up
in a later PR: "Token rotation, expiry, scopes," "Persistent storage /
database," "Real game assets (placeholders only)," "Structured logging,
metrics, observability," "Async / streaming response handling," "Rate
limiting." Its `notes.for_assistant` section records two specific, still-true
design facts: Content-Type is read from the manifest entry, not inferred from
the file extension, and a single kind can map to multiple ids (the two audio
entries demonstrate this).

## Tests — `tests/`

| Path | Scope |
|---|---|
| `tests/conftest.py` | **In** — defines the test double for the whole functional contract: a temp tokens file, a temp manifest + placeholder files, and a Flask test client wired to both via the `SASK_TOKENS_PATH`/`SASK_MANIFEST_PATH` env vars. |
| `tests/test_health.py` | **In** — confirms `/health` needs no auth and no config; already independently replicated in `sask-calendar/src/sask/web/routes.py`'s own `/health` route (added for DD-0014). Nothing to port; already converged. |
| `tests/test_auth.py` | **In** — the auth contract as tests: missing token, wrong token, malformed scheme, valid token, JSON error shape on 401. |
| `tests/test_resources.py` | **In** — the resource contract as tests: per-kind 200 + Content-Type, unknown id → 404, unknown kind → 404, non-empty body, JSON error shape on 404. |
| `tests/acceptance/conftest.py`, `tests/acceptance/test_remote.py` | **Partly in.** The deploy-facing structure (session-scoped `base_url`/`token` fixtures, TLS check) duplicates `analysis/deployment/testing-strategy.md`'s coverage. What's functionally new here: the byte-identity test (`test_image_bytes_match_local`, sha256 comparison) and the fact that every functional assertion from the unit tests is re-asserted against the live deployed service, not just smoke-tested. |
| `tests/test_validate_specs.py`, `tests/__init__.py` | Not meaningfully in scope (tooling/packaging). |

## Docs and narrative — `docs/`

| File | Scope |
|---|---|
| `docs/notes/lessons.md` | **In, heavily.** Two sections matter beyond what `analysis/deployment/deployment-architecture.md` already extracted: the "PR-002 — Local Flask service" retrospective (lines ~97-118 — app-factory/gunicorn coupling, translators paying off, `hmac.compare_digest` called out by name as a decision that held up, env-var configuration), and section 4, "Applying these lessons to a production gaming app" (lines ~206-314), which explicitly extrapolates sask's resource-server pattern toward "the resource-delivery layer of a game" with a desktop client holding a session token — directly relevant framing for a merge design, even though it predates `sask-calendar` and was written about a hypothetical, not this project. |
| `docs/devlog.md` | **In** — the PR-002 entry (~line 152) corroborates lessons.md with no material new functional content beyond it. |
| `docs/references.md` | Not read — general links. |

---

## Redesign candidates — explicitly not a port

Per the standing project guidance, resource-server code is not meant to be
imported wholesale into the calendar domain; the items below exist in `sask`,
do something real, and are flagged here precisely *because* a future design
session needs to decide to rebuild them, not carry them over:

- **The flat shared-bearer-token model (`auth.py`'s token list).** Single
  tier (valid/invalid), no scope, no expiry, no rotation without a redeploy —
  all of this is self-acknowledged as incomplete by the project's own ADR-0001
  followup and the lessons.md hardening checklist. It was adequate for a
  single-developer hobby project with one trusted client. It is not a design
  to copy forward; it's a placeholder its own author already flagged for
  replacement.
- **Per-request reload-from-disk for both tokens and the manifest** (`app.py`
  calling `load_tokens()`/`load_manifest()` inside the route handler, not at
  app-factory time). This is the one I/O pattern in sask's app that has no
  analog anywhere in `sask-calendar`'s current code — see `persistence.md`.
  Convenient for sask's hot-reload-without-restart use case; not something to
  default into without a deliberate decision.
- **`_SUPPORTED_KINDS` as a hardcoded `frozenset` in `app.py` (line 12).**
  Adding a fourth resource kind requires a code change. This directly
  contradicts `sask-calendar`'s established commitment that "all bodies,
  calendars, seasons, stars, names, and lore are defined in config; engine
  functions contain no hardcoded domain or lore data" (DD-0002 point 1,
  REQ-OPS-006). Not a pattern to carry over as-is.
- **`translators.py` as a module name and shape.** The underlying idea
  (explicit serialization functions, no auto-serializer) is already present
  in `sask-calendar` in a more developed form. The literal name collides with
  `src/sask/web/translator.py`, which does something else entirely. See
  open-questions.md item 7.
- **Poetry/`pyproject.toml` packaging specifics.** `sask-calendar` has its own
  packaging and dependency story; nothing here transfers.
- **REQ-FUN-003's deployment-acceptance content.** Already covered by
  DD-0014/SPEC-024; re-importing it as a "functional" requirement would
  duplicate existing material under a different label.
