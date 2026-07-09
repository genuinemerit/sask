# `saskan-app-alt` Design-Components Analysis

Part of the [`saskan-app-alt` → `sask` port analysis](README.md). This file evaluates
the legacy project's *documented* architecture and design — ADRs, architecture docs,
i18n design, process tooling — and scores each as still-relevant, superseded, or
aspirational/never-built. Factual inventory is in
[source-inventory.md](source-inventory.md); runtime behavior is in
[feature-analysis.md](feature-analysis.md).

## ADRs (`docs/architecture/adr/0001`–`0017`)

16 of 17 are `Status: Accepted`; only ADR-0017 (newest, logging policy) is `Draft`.
"Implemented" below means confirmed working per feature-analysis.md; "moot" means the
subsystem it describes is an empty stub with nothing built against it.

| ADR | Title | Status here | Assessment |
|---|---|---|---|
| 0001 | Hex-grid axial coordinates | Moot | `core/` is empty; no hex math exists anywhere |
| 0002 | Per-turn JSON/msgpack snapshots | Moot | No turn engine exists to snapshot |
| 0003 | JSON predicates for story triggers | Moot | Long, tutorial-like; amended in place with an "Amendments" section rather than superseded — a documentation-process pattern worth noting, not a design worth porting (no engine to trigger against) |
| 0004 | Typer CLI | **Implemented** | Best runtime-verified ADR — matches the real smoke-test transcript closely. Config precedence, exit codes, and the CLI-only-calls-client-API layering rule are real and enforced |
| 0005 | Clean layers (`ui_* → client API → infra → engine → core`) | **Implemented & enforced** | The single most concretely-enforced ADR — realized verbatim by `.importlinter` and wired into CI. Highest-value pattern in the whole ADR set |
| 0006 | Flat maps, no wrap | Moot | Lore-driven reaffirmation of 0001; no map exists |
| 0007 | Constrained procedural worldgen | Moot | Reads like an embedded tutorial/spec rather than a terse decision; no worldgen code exists |
| 0008 | Notification taxonomy | Partially realized | General taxonomy narrowed for the actual build by ADR-0014 to just `system.welcome`/`system.reject` |
| 0009 | Minimal client-server (TCP, NDJSON, thread-per-connection) | **Implemented** | Central networking ADR, directly confirmed running in the smoke-test transcript |
| 0010 | Services metadata module | **Implemented** | Canonical home of `PROTOCOL_VERSION`, `SUPPORTED_LANGS`, etc. |
| 0011 | JSON-Schema message contracts | **Implemented** | Envelope/payload schemas are real and validated at ingress |
| 0012 | Client addressing/subscriptions | Aspirational | `unicast/group/broadcast`, `idempotency_key` — none of it built; PR-2's explicit non-goals |
| 0013 | No durable message queues | **Implemented (by absence)** | Consistent with 0009/0012; ephemeral only, logs are the sole record |
| 0014 | Startup handshake/session activation | **Implemented, ties it together** | The ADR that most closely matches the live smoke-test transcript; embeds its own i18n section. One stale path reference (`saskan/docs/diagrams/...` vs. the real `docs/architecture/diagrams/...`) |
| 0015 | Asset mgmt, 3-stage storage evolution | Partially implemented | Longest, least-distilled ADR — mixes real decisions with generic research asides (DO Spaces pricing, cache-busting tutorial). Messages carry metadata+URLs, never bytes — a good pattern regardless of storage stage |
| 0016 | 3 UX shells (CLI/PyGame/PySide) | Only CLI shell real | Directly informs the i18n authoring guide. File has visible formatting corruption (stray `&#x20;` entities) |
| 0017 | Logging policy v2 (Draft) | Target state, not implemented | Best-designed, most generic (non-lore-specific) ADR in the set — good candidate to port near-verbatim as a *pattern*, adapted to a Flask request lifecycle instead of a TCP handshake lifecycle |

**Client-server story across ADRs**, called out since it's the most coherent thread:
0009 (transport) → 0010 (constants) → 0011 (schema contracts) → 0012 (addressing,
mostly aspirational) → 0013 (no durable queues) → 0014 (the ADR that actually binds
PR-2 together). This is a disciplined, deliberately-not-HTTP design — worth preserving
as reference documentation regardless of whether `sask` ever builds a literal
equivalent.

## Architecture docs (`docs/architecture/*.md`)

- **`architecture_summary.md`** — a pre-ADR "brain dump"; most of its content became
  the "Alternatives Considered" sections of ADR-0001/0002/0004. Superseded by the ADRs
  themselves; references a stale `docs/adr/` path from before a docs reorg.
- **`client_server_game.md`** — a networking-tool bake-off (asyncio vs. ZeroMQ vs.
  Twisted vs. `socketserver`), concluding in favor of `socketserver`. The brainstorming
  precursor to ADR-0009's settled decision; not needed once the decision is read.
- **`documentation_system.md`** — process notes (Markdown-for-now, defer MkDocs/
  Sphinx). No `mkdocs.yml`/Sphinx config actually exists — confirmed still "Phase 1."
  Low relevance to the port.
- **`i18n_authoring_guide.md`** — see i18n section below.
- **`ports_connections.md`** — a generic TCP port-mechanics explainer, similar in
  spirit to the excluded `docs/reference/` cheatsheets. Only saskan-specific value:
  confirms the port-7777 default.
- **`project_structure.md`** — the most operationally useful architecture doc: a
  per-package Purpose/Components/Anti-patterns/Patterns table for every `saskan/`
  subpackage, plus a closing cross-cutting "Patterns and Anti-Patterns" section
  (Functional Core/Imperative Shell, Explicit Data Contracts, Determinism by Design,
  Narrow Interfaces, vs. Leaky Abstractions/Hidden Mutation/Over-modeling). This
  operationalizes ADR-0005's layering rule into concrete responsibilities and is the
  strongest single candidate to port as a reusable architecture-reference template
  (`sask` already has an equivalent split — engine subpackages vs. consumer adapters
  vs. shared spine per its own DD-0017 — so this would be an adaptation, not an
  import).

## Feature-design docs (`docs/design/feat(*).md`)

- **`feat(first_handshake).md`** (~32KB) — the PR-2 handshake spec, rewritten 3–4
  times in different framings (CLI-flow table, ADR cross-check, design spec, CLI
  contract, PR checklist). A good worked example of ADR→implementation-checklist
  translation, but very redundant as raw content — the [feature-analysis.md](feature-analysis.md#handshake-protocol)
  section above is a distillation; the original is not worth porting wholesale.
- **`feat(first_splash).md`** — part working-log (explains why ADR-0015/0016 were
  spawned, documents a docs reorg, documents an i18n `en-EN`→`en-US` bug-fix pass,
  documents turning on GitHub CodeQL/secret-scanning), part feature spec for a
  PyGame/PySide splash screen that was never built. Its sketched file layout doesn't
  match the authoritative `project_structure.md` layout — a minor internal
  inconsistency, not a design worth carrying forward as-is.
- **`feat(greeting).md`** — not really a feature spec; a first-person runbook of
  bootstrapping the whole GitFlow+CI process using the trivial `saskan hello` command
  as the vehicle. Richest source for understanding how the branch-protection/required-
  checks scheme was configured, which matters only if that scheme itself were being
  carried forward — it is not (see Process/tooling below).
- **`docs/design/test_results/PR-2_smoke_tests.txt`** — a real terminal transcript;
  the single best piece of *evidence* in the whole legacy doc set (used throughout
  feature-analysis.md to confirm claims are runtime-proven, not just designed).

## i18n design (deep dive)

Primary sources: `i18n_authoring_guide.md`, ADR-0014's embedded i18n section, ADR-0008
(`i18n_id` field), ADR-0010 (locale constants).

- Dotted lowercase keys (`^[a-z0-9]+(\.[a-z0-9]+)*$`), namespaces `system.*`/`msg.*`/
  `ui.*`/`err.*`/`log.*`. Locales `en-US` (default)/`es-ES` via `SASKAN_LANG`. The
  guide explicitly warns `en-EN` is **not valid** — confirmed a real bug once existed
  matching exactly that mistake.
- **Internal inconsistency worth not repeating:** the authoring guide says locale
  files are JSON; the actual PR-2 implementation checklist (and the real files) use
  YAML. Pick one format explicitly for any new design — don't let the doc and the
  code disagree the way this one does.
- **Enforcement claim vs. reality:** the guide states linting/pre-commit hooks enforce
  the key-regex and no-`en-EN` rules. `.pre-commit-config.yaml` contains no such hook —
  this is aspirational, documented-but-not-wired-into-tooling.
- **Assessment on "is this gettext":** gettext-*inspired in spirit* (message-ID keys,
  per-language directory layout, env-var active locale with fallback) but **not**
  actual GNU gettext — no `.po`/`.mo`, no `msgid`/`msgstr`, no extraction tooling. A
  bespoke flat key→string table with a simple lookup-and-fallback function.
- This is the one piece of the legacy design explicitly called out by
  `refactoring_notes.md` as something `sask` should retroactively adopt — see
  [porting-roadmap.md](porting-roadmap.md).

## Process/tooling assessment

**Worth porting as enforced patterns** (adapted to `sask`'s actual module names/tools,
not copied literally):

- **`.importlinter`** — the single highest-value process artifact in the legacy repo.
  Four `forbidden` contracts turn ADR-0005's layering rule into an automatic CI gate
  (`ui_cli`/`ui_pygame`/`ui_pyside` forbidden from `engine`/`core`/`infra.net.server`/
  `infra.persistence`/`infra.schema`; `engine` forbidden from `infra`/`ui_*`; `core`
  forbidden from everything outside itself). `sask` would rewrite the contracts for
  its own `calendar/asset/help` (engine) vs. `web/api/cli` (adapters) split.
- **`.pre-commit-config.yaml`** — minimal and genuinely useful (pre-commit-hooks +
  isort + black + a local mypy-via-poetry hook), scoped sensibly (excludes `docs/`,
  `.github/`, image assets). `sask` already runs an equivalent (ruff-based) gate; the
  one real gap is `sask` currently has no `mypy` step where the legacy project did —
  flagged as an open question in [open-questions.md](open-questions.md).
- **ADR-0017's logging-policy design** — see ADR table above; best-designed, most
  generic ADR in the set, good to port as a pattern even though `sask` has zero
  logging today (greenfield, not a replacement).

**Standard artifacts** (`AUTHORS.md`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`,
`SECURITY.md`, `RELEASE.md`, `CHANGELOG.md`) — assessed individually:

- `AUTHORS.md` lists two names/aliases that are almost certainly one solo developer
  under two `pm.me` addresses. The *shape* (Development Lead / Contributors) is
  reusable if real outside contributors ever appear; the content is not.
- `CODE_OF_CONDUCT.md` — verbatim Contributor Covenant v2.1, zero project-specific
  content, simulates a team that doesn't exist. Lowest-value item to carry forward now.
- `CONTRIBUTING.md` — generic OSS boilerplate; even references `flake8`, which isn't
  actually configured anywhere. Templated, not saskan-specific.
- `SECURITY.md` — has SLA numbers (5/10 business days) implying a security team that
  doesn't exist. The *practice* (report privately, don't file a public issue) is worth
  keeping in spirit; the SLA theater is not.
- `RELEASE.md` — genuinely concrete and tool-specific (names real Makefile targets and
  Release-Drafter automation). Worth porting the *shape*, not the literal Poetry/
  Release-Drafter specifics, since `refactoring_notes.md` drops the GitHub automation
  this doc depends on.
- `CHANGELOG.md` — thin on current content, but its "Ancient History" section is real
  project archaeology (5 dated entries 2022–2025 documenting prior from-scratch
  rewrites). Useful historical context only; the Keep-a-Changelog/SemVer convention is
  the only forward-transferable part.

Per `refactoring_notes.md`'s explicit instruction ("even those should be done
explicitly, not by default"), none of these should be auto-copied — see the Port
Phase 0 decision in [porting-roadmap.md](porting-roadmap.md).

**GitHub/CI process machinery** — a complete, working "professional multi-contributor
OSS" setup (8 workflows: `ci`, `lint`, `test`, `typecheck`, `codeql`, `release-drafter`,
`publish-release`, `release-tag`; issue templates; PR template; `CODEOWNERS`;
`FUNDING.yml`) self-built and self-taught by a solo developer (confirmed: `CODEOWNERS`
is a single blanket rule, `AUTHORS.md`'s two names are one person,
`feat(greeting).md` is a first-person journal of learning GitHub Rulesets). Concretely:
`ci.yml` already runs everything `lint.yml`/`test.yml`/`typecheck.yml` do via one
Makefile target — **3 of the 4 core workflows are redundant re-runs of the same work**,
existing only so each shows up as an individually-named required status check in
branch protection. This entire area is precisely what `refactoring_notes.md` says to
drop: *"Complex interactions with GitHub ... This will continue to be a one-person
hobby project ... consciously choosing not to simulate a team structure going
forward."* Recommendation: drop all of it except the two enforcement mechanisms
already called out above (`.importlinter`, `.pre-commit-config.yaml`), which are
genuine engineering guardrails, not team-process simulation.
