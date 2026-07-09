# Open Questions

Part of the [`saskan-app-alt` → `sask` port analysis](README.md). Deferred to the
future feature-by-feature implementation sessions referenced in
[porting-roadmap.md](porting-roadmap.md). Each has a stated recommendation, but none
are locked in — resolve explicitly when the relevant phase is actually implemented.

1. **i18n retrofit sequencing.** Recommend it blocks only *new* user-facing surfaces
   (Port Phase 3), not Phases 0/1. Status: open.
2. **i18n technical shape.** The legacy design uses a silent 4-level fallback chain
   (locale → en-US → caller fallback → raw key) — arguably correct for display text,
   where a missing translation shouldn't crash a page. `sask`'s existing convention
   everywhere else is fail-fast (`ConfigError` on any missing/malformed config).
   Recommend keeping silent fallback for i18n specifically, as a deliberate exception,
   not an oversight. Status: open, flagged for confirmation in DD-0023.
3. **Locale data file format.** Recommend TOML, matching every other `sask` config
   file — the legacy project itself is inconsistent (its authoring guide says JSON,
   its actual shipped files are YAML); don't import that inconsistency. Status: open.
4. **Exact shape of Port Phase 3's API, if built.** Literal envelope/JSON-Schema port
   (per ADR-0009/0010/0011) vs. simpler idiomatic Flask/REST reusing `sask`'s existing
   message-unit types. No recommendation forced — genuinely open, and lower-priority
   than the CLI half of Phase 3 since no client exists yet to consume an API. Status:
   open.
5. **`draw/huge_barbican.py` (DALL-E concept-art script).** Recommend explicit
   out-of-scope with a one-line archival note in DD-0020 — needs a paid OpenAI API
   key, fully manual, decoupled from any pipeline. Status: leaning resolved (see Port
   Phase 0), confirm at implementation time.
6. **`mypy` gate.** Present in the legacy project's `.pre-commit-config.yaml`, absent
   from `sask`'s current `tools/dev/pre-commit-check.sh` (ruff, shellcheck,
   pymarkdown, `validate_specs.py` only). Minor, but worth a deliberate yes/no during
   Port Phase 1 rather than silent omission either way. Status: open.
7. **Analysis-folder lifecycle.** `sask`'s two historical precedents
   (`analysis/deployment/`, `analysis/functionality/`, both referenced from
   `design/decisions/dd-0014-deploy.toml` and `dd-0016-asset-retrieval.toml`) were
   deleted from disk (archived to Dropbox) once their DDs were accepted. This port is
   larger and closes out an entire sibling project, which may be a reason to keep
   `sask/design/analysis/saskan-app-alt-port/` permanently instead. Recommend
   deciding this only after DD-0020–0024 exist and are accepted, not now. Status:
   open, low priority.
8. **Granularity of Port Phase 0's DD-0020.** It currently bundles the drop-list,
   the standard-artifacts decision, and the convergent-prior-art note into one DD.
   Could instead be split into smaller, single-purpose DDs, or folded into
   `docs/devlog.md` narrative entries with no formal DD at all — `sask`'s own history
   uses both styles. Recommend one bundled DD (current proposal) since none of its
   parts individually changes any running behavior. Status: open, minor.
9. **Richer CLI output formatting.** SPEC-034 (`legacy-cli-deepening.md`) recommended
   plain `typer.echo()` uniformly, no `rich` dependency, since none of the 5 initial
   commands needed table/styled output. Noted during SPEC-034's manual UAT
   (2026-07-09): piping Markdown-formatted CLI output (e.g. `sask help <topic>`)
   through an external pager like `glow` already renders it richly in-terminal without
   any `sask` code change — visible in `docs/console_log.txt`'s side-by-side plain vs.
   `glow`-rendered output for `sask help getting-started`. A potential future
   refactor: have `sask`'s own CLI output use richer formatting directly (tables,
   styled headers) rather than relying on the user piping through an external tool —
   `rich` is already an installed transitive dependency of `typer`, so no new
   dependency would be needed if this is picked up later. Explicitly **not now** —
   the user's own framing was "a future iteration." Status: open, low priority,
   deferred.
