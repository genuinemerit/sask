# `saskan-app-alt` → `sask` Port Analysis

Analysis produced ahead of porting `saskan-app-alt` (a retired game-prototype repo)
into `sask` (the active Saskan calendar-engine app), per the governing brief at
`saskan-app-alt/docs/design/design_notes/refactoring_notes.md`. This is analysis and
planning only — no code or `sask` design-doc (dd/req/spec) TOML has been written yet.
Actual porting work happens feature-by-feature in future, separate sessions, following
`sask`'s own conventions.

**Out of scope for this analysis:** `saskan-app-alt/docs/design/Big_Picture/` — a
separate set of forward-looking design notes for `sask`'s own future development, not
part of `saskan-app-alt`'s feature set. It has no bearing on this analysis and is
being carried over to `sask` unchanged, separately from this port effort.

## Reading order

1. **[source-inventory.md](source-inventory.md)** — what the legacy repo contains:
   subsystem-by-subsystem maturity (working / stub / dead), dead code and unused
   dependencies to ignore, and an important correction — code in `sask` that
   resembles `saskan-app-alt`'s utilities actually has a different, already-resolved
   lineage (a third project, `sask-proto`), so it does not need to be re-ported.
2. **[feature-analysis.md](feature-analysis.md)** — what the *working* subsystems
   actually do: the CLI, the TCP handshake protocol, i18n, config, logging, and the
   asset-build pipeline, each covering real behavior and failure modes, not file
   layout.
3. **[design-components-analysis.md](design-components-analysis.md)** — evaluation of
   the legacy project's 17 ADRs, its architecture docs, its i18n design in depth, and
   its process/tooling (what's worth porting as a pattern vs. what's team-process
   simulation to drop).
4. **[porting-roadmap.md](porting-roadmap.md)** — the first-pass, four-phase sequenced
   plan: legacy scope closure, engineering guardrails, mandated i18n retrofit, and a
   CLI+API surface — with a proposed `sask` DD/REQ/SPEC mapping table.
5. **[open-questions.md](open-questions.md)** — decisions deliberately left open,
   each with a recommendation, deferred to implementation time.

## One-paragraph summary

`saskan-app-alt`'s directory tree suggests a full game engine; in reality, five of its
major subsystems (`core/`, `engine/`, `sims/`, `ui_pygame/`, `ui_pyside/`) are empty
scaffolding with a single commit each, and the only genuinely working, tested features
are a Typer CLI, a minimal TCP handshake protocol, a bespoke i18n lookup system (en-US/
es-ES), structured logging, and an actively-used image-asset build pipeline. Most of
the legacy project's 17 ADRs describe intent that was never built; the ones that were
built (clean layering via `.importlinter`, the CLI pattern, the handshake protocol
design) are worth porting as patterns. The GitHub/CI process machinery is exactly what
the governing brief says to drop. `sask` already independently has equivalent
utility/asset-build code via an unrelated third project (`sask-proto`), so that slice
needs no porting at all. The one mandatory carry-over is localization: `sask` has zero
i18n infrastructure today and the brief requires retrofitting it across all user-facing
text, informed by (but not copied from) the legacy i18n design. The proposed roadmap
sequences this as: close out what's being dropped, add engineering guardrails, do the
i18n retrofit, then build a `sask`-native CLI/API surface informed by the legacy
protocol design.
