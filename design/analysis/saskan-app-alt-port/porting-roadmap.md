# First-Pass Porting Roadmap

Part of the [`saskan-app-alt` → `sask` port analysis](README.md). This is a **first
pass** — a proposed sequence and mapping, not a locked-in plan. Every phase should be
re-evaluated at implementation time against `sask`'s then-current state. Nothing here
authorizes writing code or TOML docs; that happens feature-by-feature in future,
separate sessions, following `sask`'s own dd/req/spec conventions and its 4-layer
acceptance pipeline (`design/decisions/dd-0014-deploy.toml`,
`design/specs/spec-024-acceptance.toml`).

Governing constraint, from `saskan-app-alt/docs/design/design_notes/refactoring_notes.md`:
port by feature, into `sask`'s dd/req/spec conventions, with rigor matching `sask`'s
existing standard; don't copy code/docs without evaluation; drop GitHub-process
complexity; retroactively adopt localization into all `sask` user-facing text; every
"prod" feature must be deployed to DigitalOcean and pass manual acceptance review
there before being considered done.

Phases are numbered (not lettered) to avoid collision with `sask`'s own existing
internal cleanup sequence (Phase A = repo rename, B = src reorg/DD-0017, C = tools
reorg/SPEC-029, D = help guide/DD-0018).

## Port Phase 0 — Legacy scope closure

**Documentation only — no runtime code, no new tests.** Formally closes the book on
what is *not* carried forward, so the decision is recorded rather than implied by
silence:

- The drop-list: all GitHub Actions/issue-template/CODEOWNERS/release-drafter
  machinery (see [design-components-analysis.md](design-components-analysis.md));
  the five empty stub packages (`core/`, `engine/`, `sims/`, `ui_pygame/`,
  `ui_pyside/`), marked "archived, not ported" rather than silently omitted; the
  confirmed dead/superseded files (`tools/snips/assets_snip.py`, the unused manifest
  DTO layer); the ~10 declared-but-unused `pyproject.toml` dependencies.
- The standard-artifacts decision: adopt `SECURITY.md`'s private-disclosure
  *practice*, not its SLA-number content; skip `AUTHORS.md`/`CONTRIBUTING.md`/
  `CODE_OF_CONDUCT.md` unless explicitly wanted later (per `refactoring_notes.md`:
  "even those should be done explicitly, not by default").
- The convergent-prior-art note: `saskan-app-alt`'s `tools/utils/{match_semver,
  stamps,platform}.py`, `tools/validate_json.py`, and `tools/studio/build_assets.py`
  do **not** need to be ported — `sask` already has equivalent, independently-sourced,
  better-tested functionality (`tools/helpers/*`, `tools/studio/build_assets.py`) via
  a different lineage (`sask-proto`, not `saskan-app-alt` — see
  [source-inventory.md](source-inventory.md#convergent-prior-art--verify-before-porting)).
  This also closes out the legacy asset pipeline specifically: its rsync-to-a-
  separate-nginx-host serving model is not adopted because `sask` already has a
  different, already-accepted architecture for this problem (DD-0016 + SPEC-027 —
  Flask route + config-driven catalog, synced to the same droplet via Ansible).
  `draw/huge_barbican.py` (DALL-E concept art) is recorded as out of scope with a
  one-line archival note — needs a paid API key, fully manual, decoupled from
  everything.

**Proposed:** `DD-0020`. No REQ/SPEC needed — no behavior changes, nothing to test.

## Port Phase 1 — Engineering guardrails

**Pattern ports, greenfield in `sask`.** These are guardrails other work should be
built *under*, particularly important if Port Phase 3's CLI/API work proceeds — a
layering contract adopted before new adapter code exists is far more useful than one
retrofitted after.

- Adapt the `.importlinter` layering contract to `sask`'s actual module names: engine
  (`calendar/`, `asset/`, `help/`) forbidden from importing adapters (`web/`, `api/`,
  `cli/`) in the wrong direction, and vice versa; shared spine (`message.py`,
  `config_loader.py`) importable by both, per `sask`'s existing DD-0017 placement
  rule. This is a pattern port — none of `saskan-app-alt`'s module names exist in
  `sask`.
- Adopt structured logging, designed after ADR-0017's policy (event taxonomy, level/
  formatter/payload-mode env-var axes, redaction rules) but rewritten for a Flask
  request lifecycle instead of a TCP handshake lifecycle. `sask` has zero logging
  infrastructure today (confirmed, see [source-inventory.md](source-inventory.md)) —
  this is greenfield, not a replacement.

**Proposed:** `DD-0021` (layering) → `REQ-OPS-019` → `SPEC-032`; `DD-0022` (logging) →
`REQ-OPS-020` + `REQ-SEC-004` (log output must not carry secrets/PII — ADR-0017's own
redaction section justifies a security requirement here) → `SPEC-033`.

**Depends on:** nothing. **Acceptance:** CI/pre-commit green with the new contract
active; a deliberate temporary violation should demonstrate the contract fails closed.
Minimal DO-deploy gate — a redeploy confirming the added steps don't break the
pipeline.

## Port Phase 2 — i18n infrastructure and retrofit

**The mandated cross-cutting thread** — `refactoring_notes.md` makes this
non-optional: *"retroactively adopting localization into all user-facing
text-containing sask interfaces."*

- A new shared-spine locale module (not nested under `web/`/`api/`/`cli/`, per
  DD-0017's own engine/adapter/shared-spine logic, since it must serve every consumer
  adapter) implementing locale lookup with fallback.
- A retrofit pass over `base.html` (removing the hardcoded `lang="en"`), all 7
  existing templates, and the `help/` markdown-rendering path.
- Sequenced after Phase 1's guardrails (good practice, not a hard dependency) and
  before Phase 3, so no new user-facing surface gets built i18n-naive and needs a
  second retrofit later. Does not need to block Phase 0 or 1, neither of which touch
  user-facing text.

**Proposed:** `DD-0023` → `REQ-FUN-014` (all user-facing text sourced from localized
lookups, not hardcoded) + `REQ-OPS-021` (locale selection/fallback mechanism) →
`SPEC-034` (infrastructure) + `SPEC-035` (retrofit) — two SPECs under one DD mirrors
the existing DD-0014 → SPEC-022/023 infrastructure-vs-application split.

**Depends on:** Phase 1 (loosely). **Blocks:** Phase 3. **Acceptance:** this is the
largest-diff phase (touches nearly every template) — redeploy, manually confirm both
locales render correctly on live pages (the spiritual descendant of the legacy
project's own `SASKAN_LANG=es-ES` smoke test, but against real `sask` pages), confirm
`<html lang>` reflects the active locale, confirm the existing acceptance suite
(`tools/ops/acceptance-test.sh`, `tests/acceptance/`) still passes with no functional
regression, record in `tests/results/<SPEC-ID>.md`.

## Port Phase 3 — CLI + API surface

Per explicit decision (not archived): a real future phase using `sask`'s already-
reserved empty `src/sask/cli/` and `src/sask/api/` stubs.

- **CLI:** a `sask`-native command set under `src/sask/cli/`, inspired by ADR-0004's
  Typer pattern and exit-code convention, but wrapping `sask`'s *existing* engine
  (e.g. `sask ephemeris`) rather than literally porting `hello`/`start`/`connect` —
  those commands exist only to drive the handshake protocol, which has no `sask`
  equivalent to wrap.
- **API, if warranted:** informed by the envelope/JSON-Schema-contract pattern
  (ADR-0009/0010/0011) — message shape, explicit versioning, schema validation at the
  boundary — but reusing `sask`'s existing message-unit pattern (`message.py`) rather
  than a TCP handshake protocol, since `sask` is a stateless Flask app with no
  multiplayer/session need. The exact shape (literal envelope port vs. simpler
  idiomatic Flask/REST) is left open — see [open-questions.md](open-questions.md).
- Preserve the `ServerState` (READY/DRAINING/STOPPED) lifecycle concept and the
  JSON-Schema-validated-envelope pattern as reference documentation
  ([design-components-analysis.md](design-components-analysis.md)) regardless of
  exactly how much of it gets built.

**Proposed:** `DD-0024` → `REQ-FUN-015` → `SPEC-036`.

**Depends on:** Phase 2 (so any new user-facing CLI/API output is i18n-aware from
birth). **Acceptance:** full SPEC + redeploy + acceptance-suite pass per `sask`'s
standard pipeline, same as any other feature.

## Dependency summary

Phases 0 and 1 have no dependencies on each other or on Phase 2, and can run in any
order or in parallel. Phase 2 is the one true cross-cutting gate, blocking only Phase
3. Phase 3 depends on Phase 2. Every phase that changes runtime behavior gets its own
SPEC and must be redeployed to the live droplet and pass acceptance review there
before being considered done, per `refactoring_notes.md`'s explicit requirement.

## Proposed DD/REQ/SPEC mapping (first pass, renumber freely)

Next-available IDs confirmed at analysis time: `dd-0020`, `req-fun-014`,
`req-ops-019`, `req-sec-004`, `spec-032`.

| Phase | DD | REQ(s) | SPEC(s) |
|---|---|---|---|
| 0 | DD-0020 — legacy scope closure | — | — |
| 1 | DD-0021 — import-layering contract | REQ-OPS-019 | SPEC-032 |
| 1 | DD-0022 — structured logging | REQ-OPS-020, REQ-SEC-004 | SPEC-033 |
| 2 | DD-0023 — i18n infrastructure & retrofit | REQ-FUN-014, REQ-OPS-021 | SPEC-034, SPEC-035 |
| 3 | DD-0024 — CLI + API surface | REQ-FUN-015 | SPEC-036 |
