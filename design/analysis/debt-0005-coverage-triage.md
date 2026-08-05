# DEBT-0005 — test-coverage triage

**Round:** FIX-and-analyze round, DEBT-0004 & DEBT-0005 (see
`design/debt/000-FIX-and-analyze-instruction.md`). This is a triage record, not a
coverage-percentage chase — coverage stays informational (`poetry run pytest --cov`),
not wired into `pre-commit-check.sh` or CI.

**Baseline:** 91% overall (line+branch) across `src/sask`, recorded at DEBT-0005's
raising (2026-08-02). **After this round:** 92% overall; the modules below moved from
55-78% to 62-100%. The number moved as a side effect of closing real gaps, not as the
goal.

Each module below got a deliberate call: **real gap, worth a test** vs. **trivial glue /
cosmetic, acceptable to leave thin**. Targeted tests were added only for the former.

---

## Higher-priority modules (per the FIX instruction)

### `src/sask/i18n/catalog.py` — 78% → 100%

The shared locale-resolution seam every adapter depends on. Two real, never-hit branches:

- `resolve()`'s `if locale != catalog.base_locale` guard (line 32) was never exercised
  with `locale == catalog.base_locale` and a missing tag — every existing test resolved
  against a *non-base* locale. **Verdict: real, worth a test** (confirms the base-locale
  short-circuit still lands on the raw-tag fallback rather than looping or raising).
  Added `test_resolve_against_base_locale_directly_skips_redundant_fallback`
  (`tests/test_spec_035.py`).
- `best_locale()`'s loose language-only prefix match (lines 63-65, e.g. bare `es`
  matching a declared `es-ES`) and its "header present but matches nothing at all"
  fallback (branch 58→67) were both untested — the one existing Accept-Language test
  leads with an exact `es-ES` match, resolving before either branch is reached.
  **Verdict: real resolution logic, not glue** — this is exactly the kind of locale
  negotiation a real browser/client Accept-Language header can produce. Added
  `test_best_locale_loose_language_only_match` and
  `test_best_locale_falls_back_to_base_when_header_matches_nothing`
  (`tests/test_spec_035.py`).

### `src/sask/cli/_subprocess.py` — 56% → 100%

`run_tool()`'s actual `subprocess.run()` call, its exit-code propagation, and the
launcher-not-found `FileNotFoundError` branch (lines 48-54) were entirely untested:
every command test monkeypatches `run_tool` away before it ever runs, and the one
existing subprocess test covered only the missing-*script* early exit (a distinct,
already-tested guard). **Verdict: real, untested error path** — exactly the class of
gap that bit in production once already (see the missing-script regression test's own
docstring). Added `test_run_tool_propagates_exit_code_of_the_real_subprocess` (a real
script exiting non-zero, confirming the exit code survives) and
`test_run_tool_reports_clean_error_when_launcher_not_found` (bogus launcher, confirming
the clean error message) to `tests/test_spec_038.py`.

### `src/sask/cli/formatting.py` — 55% → 62%

Two distinct gaps, two different verdicts:

- Lines 31-32 (`echo_dict` called with an empty `data` dict) directly guard
  `max(len(str(key)) for key in data)` a few lines below — without the early return, an
  empty dict would raise `ValueError`. **Verdict: not glue, a crash guard** — every real
  caller happens to always pass non-empty data today, so this was a live, untested
  landmine. Added `test_echo_dict_empty_data_does_not_crash` (`tests/test_spec_038.py`).
- Lines 38-46 and 52 are the rich-terminal-styling branches (`_console.is_terminal` /
  `_err_console.is_terminal` true). **Verdict: cosmetic, acceptable to leave thin** —
  this is a systemic, already-accepted gap across the whole CLI, not new debt introduced
  by this module: `help.py`'s own terminal-rendering branch has the exact same
  characteristic (confirmed by grep — no test anywhere in the suite ever sets
  `is_terminal`/`force_terminal`, since `CliRunner` never presents a tty). Styling is
  explicitly additive (DD-0025) and produces no behavior difference a script could
  observe; testing it would mean building a synthetic-tty harness solely for this round,
  disproportionate to a "few relatively minor" FIX round.

## Lower-priority modules (confirmed, not assumed)

### `src/sask/cli/commands/logs.py` — 71% → 91%

Spot-checked against `_subprocess.py`'s exact gap shape: `logs query`'s and `logs
verify`'s own `subprocess.run(["journalctl", ...])` calls, non-zero-exit handling, and
`FileNotFoundError` handling (lines 96-112, 163-171) were untested — only the pure
`_build_journalctl_argv`/`_line_matches_level` helpers were. **Verdict: real, same class
as `_subprocess.py`** — reclassified up from the round's "likely acceptable to leave
thin" starting guess once inspected, since journalctl genuinely can be absent or exit
non-zero on a misconfigured host. Added four tests to `tests/test_spec_038.py`
(non-zero exit and missing-journalctl, for both `query` and `verify`), monkeypatching
`logs_module.subprocess.run` — the same technique the file's existing `logs verify`
tests already use.

Remaining thin spot, left as-is: lines 109-112 (`logs_query`'s `--level` filter
application over `result.stdout`) is a one-line `filter()` wiring an already
fully-unit-tested predicate (`_line_matches_level`, covered directly by
`test_line_matches_level_only_matches_wellformed_json`) into the command. Thin
plumbing over tested logic, not a new error path — left thin.

### `src/sask/cli/commands/asset.py` — 72% → 79%

- Lines 36-37 (`asset list` with an empty catalog) is a real, cheap, user-visible
  behavior branch distinct from the populated-table path. **Verdict: worth a test** —
  added `test_asset_list_reports_empty_catalog_message` (`tests/test_spec_034.py`),
  substituting a fake config since the real catalog is never empty.
- Lines 53-59 are the same rich-Table cosmetic branch as `formatting.py` — left thin for
  the same systemic reason.

### `src/sask/config_loader.py` — 87% (unchanged)

Spot-checked ~15 of the 47 missing lines across different config sections (time
constants, fatunik/terpin calendars, stars, houses, comets, i18n, spark, settings, era,
months, week, format). Every single one is the same shape: `if not isinstance(...) or
<malformed>: raise ConfigError(...)`. **Verdict: confirmed trivial, structurally
repetitive validation glue** — exactly what the round's "do not chase the number, do
not test-farm identical guards" constraint describes. Left thin, no tests added.

### `src/sask/calendar/scene.py` — 86% (unchanged) / `src/sask/calendar/lore.py` — 91% (unchanged)

Spot-checked the missing lines: comet/spark visibility toggles, a lunar-phase boundary
edge, a mood-tag fallback, an English-ordinal edge case, and (in `lore.py`) two
`ValueError` guards on an unknown `calendar_id`. The domain logic itself is already
well-covered by the existing calendar test suite; the `calendar_id` guards are
defensive invariants (the value is only ever produced by already-validated internal
config, never external input) rather than a reachable production error path the way a
missing CLI script or launcher is. **Verdict: acceptable to leave thin** — explicitly
lower priority in the round's own framing ("likely acceptable... but confirm"), and
adding narrow tests for each remaining engine-logic branch would be scope creep beyond
this round's "thin, scoped changes only" discipline.

---

## Summary

Reviewed all 8 modules the round named. Added 11 targeted tests across 5 modules for
genuine untested error/behavior paths (`catalog.py` x3, `_subprocess.py` x2, `logs.py`
x4, `formatting.py` x1, `asset.py` x1). Left the remaining gaps thin by deliberate
decision, documented above. Coverage moved from 91% to 92% as a byproduct, not a target;
it remains informational, no gate added anywhere.
