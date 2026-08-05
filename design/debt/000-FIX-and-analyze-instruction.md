# Fix-and-Analyze Round — DEBT-0004 & DEBT-0005

**Type:** Lightweight fix-and-analyze round (no design docs / no DD-REQ-SPEC set).
**Scope:** Close the two remaining open technical-debt items that are small fixes or
analysis. **DEBT-0006 (the structured API reference page) is NOT part of this round** —
it is a separate dev round with its own design docs.

This round has three pieces of work: a bug fix, a principled decision-to-decline, and a
coverage triage. Follow the existing verify discipline throughout (full suite green at the
new count; pre-commit and `validate_specs` clean; append a devlog entry).

---

## Part 1 — DEBT-0004(1): fix the `sask help` index locale bug  *(FIX)*

**Defect:** `sask help` with **no topic** (the index) always renders the base
`docs/help/index.md` regardless of `--lang` / `SASK_LOCALE`, even though
`docs/help/index.es-ES.md` exists and the web `/help` route already serves the localized
index correctly.

**Root cause (already diagnosed in the register):** in
`src/sask/cli/commands/help.py`, `_render_help`'s **topic-is-None branch** calls
`index_path()` directly and never consults `discover_parallel_docs()` — unlike its own
**per-topic branch** a few lines below, which does the locale lookup correctly, and unlike
the web index route in `src/sask/web/routes.py`, which looks up
`parallel_docs.get(("index", g.sask_locale))` before falling back to base.

**Fix:** make the topic-is-None branch do the same locale-aware lookup the per-topic branch
and the web route already do — resolve `("index", <locale>)` via `discover_parallel_docs()`,
and fall back to the base index when no locale-specific index exists. This is a
**same-mechanism fix within DD-0022**, not an architecture change. Do not introduce any new
localization mechanism; mirror the existing per-topic / web-route pattern exactly.

**Verify:**
- `sask help --lang es-ES` (no topic) renders `docs/help/index.es-ES.md`.
- With a locale index absent, it falls back cleanly to the base index.
- `sask help <topic> --lang es-ES` still works (do not regress the per-topic branch).
- Add or extend a test asserting the index honors the locale (and the fallback).

---

## Part 2 — DEBT-0004(2): Typer's own `--help` localization  *(WONTFIX, record the reasoning)*

**Decision: do NOT localize Typer's auto-generated `--help` output** (the command list,
command descriptions, and option help text).

**Reasoning (record this, so it does not resurface as an open question):** DD-0022's
localization boundary is **origin-based — localize what the end USER reads, not what the
OPERATOR reads.** Typer's `--help` chrome is the operator/developer's interface to the tool
itself, the same category as log messages, which are deliberately not localized. So `--help`
chrome is operator-facing and stays English by the same principle that keeps logs English.
This also avoids the costly implementations the register flagged (per-locale docstrings
selected at import time, or intercepting Typer's help formatter) — both of which fight the
framework for operator-facing text that the boundary says should not be localized anyway.

**Action:** do **not** implement any `--help` localization. Record the reasoning above (a
brief note in `CLAUDE.md` or the relevant CLI doc that `--help` is intentionally English-only
as operator-facing text is appropriate), and resolve DEBT-0004's `open_subquestion`
accordingly.

*(If there is ever a real population of non-developer, non-English-native users for whom the
CLI `--help` is a primary interface, this can be revisited — but that is not the current
audience, so it is declined now, not deferred as an open question.)*

---

## Part 3 — DEBT-0005: test-coverage triage  *(ANALYZE — triage, do not chase the number)*

**This is an investigation, not a fix. The deliverable is documented triage DECISIONS, not a
coverage percentage.**

**Hard constraints:**
- **Do NOT chase the coverage number.** Writing tests purely to move the percentage on
  trivial glue is make-work and is explicitly out of scope.
- **Do NOT wire a coverage threshold into `pre-commit-check.sh` or CI.** Coverage stays
  **informational** this round. A coverage gate is a separate policy decision with real
  friction cost and is not part of this work.

**Process:** go module-by-module through the low-covered files from the DEBT-0005 baseline.
For each notable gap, make a **deliberate call** and record it: *"real untested error path,
worth a test"* vs. *"trivial glue / passthrough, acceptable to leave thin."* Then add
targeted tests **only** where the triage says a gap is a real, worth-covering path.

**Look hardest at these (higher stakes than the raw percentage suggests):**
- `src/sask/i18n/catalog.py` (~78%) — the shared locale-resolution seam every adapter
  depends on. Untested branches here matter more than glue; check specifically what
  resolution/fallback branches are uncovered.
- `src/sask/cli/_subprocess.py` (~56%) and `src/sask/cli/formatting.py` (~55%) — thin
  wrappers, BUT check whether the gaps are trivial passthroughs (acceptable) or untested
  **error paths** (e.g. missing-script, non-zero-exit) — the latter are exactly the kind of
  path that bites in production and are worth a test.

**Lower priority (likely acceptable to leave thin, but confirm):**
- `src/sask/cli/commands/logs.py` (~71%), `.../asset.py` (~72%).
- `src/sask/config_loader.py` (~87%) — mostly malformed-config validation branches;
  plausibly acceptable thin.
- `src/sask/calendar/scene.py` (~86%), `src/sask/calendar/lore.py` (~91%).

**Deliverable:** an analysis file (e.g. `analysis/debt-0005-coverage-triage.md`) that lists
each reviewed module, the triage decision, and a one-line rationale — plus any targeted tests
added for gaps judged real. **A fully acceptable outcome is:** "reviewed all listed modules,
added N targeted tests for genuine error paths, left trivial glue thin by decision, coverage
remains informational." That is a complete resolution, not a shortfall.

---

## Register updates & close-out

- **DEBT-0004 → `resolved`.** Part 1 fixed; Part 2 declined-with-reasoning (resolve its
  `open_subquestion` with the origin-boundary rationale above).
- **DEBT-0005 → `resolved`.** Triage complete; targeted tests added where warranted; the
  analysis file is the record.
- Set `resolved_by` for both. **NOTE — decide the reference:** this round is not a numbered
  SPEC, so `resolved_by` should point to a traceable artifact — recommend the **devlog entry
  for this round** (and, for DEBT-0005, also the `analysis/debt-0005-coverage-triage.md`
  file). Confirm the convention you want before writing the field.
- Append a **devlog entry** summarizing the round: the index-locale fix, the `--help`
  wontfix decision and its reasoning, and the coverage-triage outcome (modules reviewed,
  tests added, decisions).

## Standing discipline
- Thin, scoped changes only — no architecture changes, no new dependencies, no coverage gate.
- Full test suite green at the new count; `pre-commit` and `validate_specs` clean.
- Do not touch DEBT-0006 (API reference) — separate round.
