# Dev log

## 2026-07-13 — SPEC-035 accepted: prod deploy + redeploy verified, DD-0022/SPEC-035 → accepted

Deployed the i18n port to the live droplet via `tools/ops/deploy.sh`
(in-place converge, not a rebuild): `pre-commit-check.sh` clean beforehand
(including the new `validate_i18n` permissive-mode step), Ansible run
`ok=40 changed=6 failed=0`, `acceptance-test.sh` 5/5 pass.

TC-035-07 then confirmed manually by the user directly against
`https://sask.davidstitt.net`: locale toggle changes nav/`/pulse`
label-sentence-paragraph copy, `/sky` season name renders localized,
help page falls back/serves its es-ES parallel doc correctly — all
matching dev behavior exactly. `sask --lang es-ES season --pulse N` over
SSH on the droplet matched the web adapter's result for the same pulse,
confirming the one-message-unit/two-adapters canary holds in production,
not just under the test client. All 7 SPEC-035 UAT cases now PASS
(`docs/user_testing.md`).

Per SPEC-035's own `design_doc_status` deliverable: `DD-0022` and
`SPEC-035` set to `status = "accepted"`. Recap of what shipped (full
detail in the 2026-07-10 entries below): shared TOML i18n catalog +
locale-parameterized resolver (`src/sask/i18n/{catalog,tags}.py`),
parallel-document help localization (REQ-SEC-005 path-safe), web
(cookie/Accept-Language toggle) and CLI (`--lang`/`SASK_LOCALE`)
adapters drawing from one shared catalog, the three-severity validator
wired into both `pre-commit-check.sh` (permissive) and `deploy.sh`
(`--strict`, pre-deploy gate), and the dual-mechanism canary (tags at
three sizes, one localized engine result on both adapters, one es-ES
help doc). Two pre-implementation analyses resolved the format
question (TOML, not the legacy JSON/YAML inconsistency) and the
tag-vs-identifier hop (engine emits tags directly; the inventory found
the mapping is uniformly 1:1). Bulk translation of existing content
beyond the canary remains an explicit follow-on SPEC, not done here.

Immediately followed by `tools/ops/redeploy.sh -y` (full destroy/
recreate/deploy/acceptance-test cycle, not just a converge) to confirm
the i18n port survives a from-scratch droplet build the same way
SPEC-032's logging port did: OpenTofu recreated the droplet, the full
`site.yml` play ran `ok=45 changed=39 failed=0`, and `acceptance-test.sh`
(run automatically at the end of `redeploy.sh`) passed 5/5.

Spot-checked i18n specifically on the freshly recreated droplet
(the generic acceptance suite doesn't exercise it): `config/i18n/
{en-US,es-ES}.toml` present, and `sask --lang es-ES season --pulse 0`
returned the localized Spanish result (`Reverdecer`) with `locale:
es-ES` threaded through correctly — confirming the catalog and CLI
adapter survive a clean rebuild, not just the box they were first
verified on. The structured log line emitted alongside it stayed
English/JSON, confirming operator-facing output remains unlocalized on
the rebuilt host too.

Both the in-place `deploy.sh` path and the full `redeploy.sh` path are
now verified against a live droplet, matching the discipline of every
prior port round (SPEC-031, SPEC-032, SPEC-034).

## 2026-07-10 — SPEC-035: local UAT passed (TC-035-01–06); droplet check pending deploy

Formal UAT recorded in `docs/user_testing.md` (SPEC-035 section,
TC-035-01 through TC-035-07). User ran TC-035-01 through TC-035-06 on the
dev host — all PASS, no notes requiring fixes. TC-035-07 (live site
toggle + `sask season` on the droplet, confirming production behaves
identically to dev) is correctly still PENDING — the i18n machinery
hasn't been deployed yet. `DD-0022` and `SPEC-035` stay `"proposed"`
until TC-035-07 closes out after the upcoming deploy/redeploy round.

## 2026-07-10 — SPEC-035: i18n machinery + dual-mechanism canary (pending manual UAT)

Fourth and final mandated functional area of the `saskan-app-alt` port
(after logging, CLI). `DD-0022`/`REQ-FUN-015`/`REQ-OPS-021`/`REQ-SEC-005`
were unusually thorough already — this was faithful implementation
against an already-settled design, not re-design.

**Two pre-implementation analyses first, per SPEC-035's own ordering**, in
`design/analysis/saskan-app-alt-port/` (same folder as the CLI round's
analyses, unprefixed): `legacy-i18n-deepening.md` resolves the legacy
JSON/YAML inconsistency in favor of TOML, flags the `fallback or i18n_id`
truthiness bug (fixed with explicit `None`-checks in the new resolver),
and identifies the one genuine architectural anti-pattern not to
repeat — legacy's global `os.getenv()` locale selection only worked
because its server never localized anything itself (shipped tags, a
single-user CLI client resolved them after the fact); `sask`'s web
adapter localizes per-request in a concurrent worker, so the new resolver
takes locale as an explicit argument, never global state.
`i18n-content-inventory.md` tiers every user-facing string (~140 LABEL,
~30 SENTENCE, ~2-3 STATEMENT) and flags the one real finding:
`scene.py::render_night_summary()`/`render_image_prompt()` are genuinely
composed prose (real English pluralization/list-joining baked into
Python control flow — `"stars" if n != 1 else "star"`), not simple tag
substitution — decomposition is explicitly deferred to a bulk-translation
follow-on, not this round. Resolves DD-0022's deferred tag-vs-identifier
question: `translator.py`'s lookup tables and `season_info()`'s
`season_id` are uniformly 1:1, so the engine already emits domain
identifiers and the adapter boundary is the "thin render-layer" the
design anticipated.

**Two design points the docs left open were put to the user, not
assumed:** (1) locale storage — a plain unsigned cookie, not a signed
Flask session, avoiding new `SECRET_KEY` secret-management footprint for
a value with no confidentiality requirement (always re-validated against
the known-locale set on read); (2) the canary's "one message unit, both
adapters" proof — a new `sask season --pulse N` command wrapping
`season_info()` directly (mirrors how `convert` wraps `pulse_info()`),
rather than overloading `convert` with an unrelated message unit.

**Shared-spine machinery** (`src/sask/i18n/{catalog,tags}.py`): `resolve(tag,
locale, catalog)` — locale → base (en-US) → raw tag, explicit `None`-checks
throughout (not truthiness), no Flask/engine/cli imports (new AST
layer-purity test). No separate cache layer — the catalog loads once at
`load_config()` time like every other config concern, exactly like
`AssetCatalogConfig`'s existing precedent it was built to match.
`config/i18n/{en-US,es-ES}.toml` — flat dotted-key `[tags]` tables (first
subdirectory under `config/`, previously flat). `config_loader.py`'s
`_load_i18n_catalog()` enforces malformed-tag-regex and missing-base-content
as load-time `ConfigError`s (hard errors everywhere, per DD-0022); missing
non-base translations are NOT a load-time concern — that's the standalone
validator's job.

**Parallel documents** (`help/loader.py::discover_parallel_docs()`): exact
same known-set-at-startup + membership-lookup-only shape as
`discover_topics()`/the asset catalog (REQ-SEC-005) — `{topic}.{locale}.md`
naming (`getting-started.es-ES.md`), locale used only as a dict key, never
path-joined. A traversal-safety test confirms a crafted locale value
reads nothing outside the known set. `discover_topics()` itself was
extended to exclude locale-suffixed files from being mistaken for their
own base topics (a real collision that would have occurred without this:
`Path.stem` on `getting-started.es-ES.md` is `"getting-started.es-ES"`,
which the original glob-and-key-by-stem logic would have surfaced as a
bogus fourth help topic).

**Web adapter**: `before_request` locale binding (cookie → Accept-Language
→ base locale, mirroring the existing logging-context-binding hook's
shape, not replacing it), a `?locale=` toggle persisted via
`response.set_cookie()`, a `context_processor` exposing `t(tag)` to
templates, `base.html`'s `<html lang>` now dynamic. `/sky`'s season
display resolves `season_id` → tag → localized text at render time;
`season_id` itself is untouched, still locale-neutral engine output.

**CLI adapter**: `--lang`/`SASK_LOCALE` as a Typer root-callback option
using `envvar=` (Typer's native flag-overrides-env-var precedence, no
hand-rolled logic, unlike `SASK_LOG_LEVEL` which has no flag counterpart);
resolved locale threads via `ctx.obj` to `season`/`help`. New
`src/sask/cli/commands/season.py`. `help`'s parallel-doc selection mirrors
the web route exactly.

**Validator** (`tools/dev/validate_i18n.py`) — self-contained, no `sask`
package import (mirrors `validate_specs.py`'s convention, since
`pre-commit-check.sh` invokes it via bare `python3`, not `poetry run`):
malformed tags and missing-base content are hard errors always; missing
non-base translations warn in permissive mode (the new pre-commit step)
and hard-fail with `--strict` (a new fail-fast step in `deploy.sh`,
before `export-requirements.sh`/`ansible-playbook`, alongside the existing
`infra.env`-exists precondition — a pre-deploy correctness gate, not a
live-HTTP check like `acceptance-test.sh`). The real committed catalog
passes `--strict` cleanly (verified by a dedicated test,
`test_real_catalog_passes_strict_validation` — the canary must not fail
the gate it introduces).

**Tests**: `tests/test_spec_035.py`, 28 tests (fallback chain, one
message unit rendering differently per locale on both adapters, parallel-
doc selection + REQ-SEC-005 traversal safety, validator severities in
both modes, locale selection on both adapters, layer purity). Found and
fixed two pre-existing test fixtures (`test_spec_002.py`,
`test_spec_026.py`) that built synthetic `config/` directories via a flat
`*.toml` glob — didn't include the new `config/i18n/` subdirectory,
breaking `load_config()` for those fixtures; fixed with `shutil.copytree`.
Full suite: 776 passed. Pre-commit clean, including the new
`validate_i18n` step.

**Manually verified locally** (not yet the formal UAT): the real Flask
dev server (not just the test client) via curl — locale toggle, `/sky`
season name, help parallel-doc/fallback all confirmed end to end; both
`poetry run sask` and `python -m sask.cli` invocations of `season`
confirmed with `--lang`, `SASK_LOCALE`, and flag-overrides-env-var.

**Not done in this pass, deliberately:** no bulk translation beyond the
canary (a follow-on SPEC, per DD-0022/SPEC-035's own explicit scope). No
decomposition of `scene.py`'s composed prose. No deploy/redeploy yet —
`design/decisions/dd-0022-i18n.toml` and `design/specs/spec-035-i18n.toml`
stay `"proposed"` until the manual UAT (`docs/user_testing.md`'s SPEC-035
section) and the deploy/redeploy round confirm the strict-mode gate and
live behavior, matching the discipline of every prior port round.

## 2026-07-09 — CLI UX follow-up: consistent `Usage: sask` in both environments

Third UX finding from Dave's droplet UAT: `sask --help` on the droplet
showed `Usage: python -m sask.cli [OPTIONS] COMMAND [ARGS]...` — Click's own
prog_name auto-detection reports "python -m sask.cli" for -m invocations
(what the /usr/local/bin/sask wrapper actually runs under the hood, since
the droplet never pip-installs the sask package itself) vs. "sask" for a
real console script (`poetry run sask` in dev, which already worked and
already showed the clean form — confirmed by re-checking, not assumed).
Fixed by pinning `app(prog_name="sask")` in `main()`, so `--help` output is
now identical in both environments regardless of the underlying invocation
mechanism. New regression test:
`test_help_usage_line_says_sask_not_python_dash_m`. Full suite: 748 passed.
Verified live: `sask --help` on the droplet now shows `Usage: sask ...`;
`acceptance-test.sh` still 5/5 PASS.

Clarified for Dave (not a doc fix — `docs/user_testing.md`'s TC-034 steps
already used this form throughout): the local equivalent of the droplet's
`sask ...` is `poetry run sask ...`, not `python -m sask.cli ...` — the
latter is what `__main__.py`/the droplet wrapper use internally so the CLI
runs without a pip-installed package, not the recommended everyday dev
command. `poetry run sask` already gets you the same typed command as the
droplet, modulo the `poetry run` prefix (standard for any poetry-managed
project; not itself something to reconcile away).

## 2026-07-09 — CLI UX follow-up: logs to stderr, not stdout

Second UX finding from Dave's own droplet UAT: `sask asset info json
varkaar-questions` printed `config_loader`'s "config loaded" JSON log
record ahead of the actual asset descriptor block, on every command. Root
cause: `main()` called `logsetup.configure()` with its stdout default, same
as `create_app()` — correct for the web app (gunicorn's stdout is captured
by journald, invisible in normal use) but wrong for the CLI, which is a
fresh process per invocation run directly at a terminal, so that same
stdout stream *is* the terminal, and every command reloads config fresh
(no long-lived process to load it once). Put a design question rather than
silently deciding: leave as-is / suppress by default with a --verbose flag
/ route to stderr. **Chose stderr** — standard diagnostics-vs-results
split, doesn't touch the web app's stdout-to-journald behavior at all, and
a plain terminal still shows both streams together (unchanged visual
experience) while `sask ... > file` or piping stdout now stays clean.

Fix: `sask.cli.main()` now calls `logsetup.configure(stream=sys.stderr)`.
New regression test `test_cli_logs_go_to_stderr_not_stdout` (subprocess-based,
asserts "config loaded" absent from stdout, present in stderr). Full suite:
747 passed. Verified locally (stdout/stderr split via redirection) and live
on the droplet (`sask asset info json varkaar-questions` — the user's exact
example — clean on stdout when redirected, both streams shown together
otherwise); `acceptance-test.sh` still 5/5 PASS.

## 2026-07-09 — CLI UX follow-up: `sask` wrapper on the droplet

Dave's own manual UAT pass on the droplet (post-acceptance, running his own
`apt` updates in the same session) surfaced a reasonable UX gap: typing
`PYTHONPATH=/opt/sask/src /opt/sask/.venv/bin/python3 -m sask.cli ...` every
time is exactly the friction the wrapper-free invocation was always going
to cause. Fixed with a small root-owned wrapper,
`ansible/roles/runtime/templates/sask-cli-wrapper.sh.j2` →
`/usr/local/bin/sask` (mode 0755): `exec env PYTHONPATH=... .venv/bin/python3
-m sask.cli "$@"`. Not a real pip/poetry console script (the droplet still
doesn't install the `sask` package itself — same deploy model as before,
unchanged); just a thin `exec` wrapper, one new Ansible task in
`roles/runtime/tasks/main.yml`, applied via `deploy.sh` and verified live:
`sask --help` and `sask logs query --unit sask -n 5` both work directly
over SSH, `acceptance-test.sh` still 5/5 PASS (no web-app impact — this
only adds a file under `/usr/local/bin`). `docs/user_testing.md`'s
TC-034-06 action steps updated to the simpler form.

## 2026-07-09 — DD-0021/SPEC-034 accepted: droplet verified, two real gaps found and fixed

TC-034-06 closed out; both `DD-0021` and `SPEC-034` set to `"accepted"`. Two
genuine gaps surfaced during deploy — neither was guessed at; both
investigated and fixed before re-verifying, same discipline as SPEC-032's
live-deploy history.

**Gap 1 — `sask --help` failed on the droplet with "No such file or
directory".** The `pyproject.toml` console script (`sask = "sask.cli:main"`)
only exists where the `sask` package itself is pip/poetry-installed with
entry points — true in dev (`poetry install`), but the droplet's `app` role
installs only `requirements.txt`'s dependencies and runs the app via
`PYTHONPATH` (matching how `wsgi.py` already works), never pip-installing
`sask` itself. Fixed with `src/sask/cli/__main__.py`, so `python -m
sask.cli` works via plain module import on both environments without
changing the deploy/install model. Covered by a new regression test
(`test_runnable_via_python_dash_m`, subprocess-based). Full suite: 746
passed.

**Gap 2 — even after that fix, nobody could actually run it as themselves.**
Tried `sudo -u sask python3 -m sask.cli logs query`: `journalctl` failed
("insufficient permissions") because the `sask` service account is
deliberately unprivileged (no journal access, by design). Tried running as
`dave` (the admin/SSH user) directly instead: failed differently — `dave`
couldn't even reach `/opt/sask/.venv` (`0750 sask:sask`), and `dave` has no
*passwordless* sudo, so journalctl's own suggested fix ("users in groups
`adm`, `systemd-journal` can see all messages") didn't apply either. Two
architecturally real questions, put to Dave rather than guessed:

1. Journal read access: group membership (`systemd-journal`) vs. baking
   `sudo` into the CLI's own `journalctl` call vs. defer. **Chose group
   membership** — matches journalctl's own suggested remedy, keeps `logs
   query` genuinely passwordless/non-interactive like the rest of the
   admin-tier commands, and avoids embedding a privilege-escalation call
   inside general-purpose CLI code.
2. App-tree read access (venv/src, needed just to invoke the CLI at all):
   add `dave` to the `sask` app group (tree-wide read, including wherever
   real secrets eventually land once auth exists) vs. loosen only the
   venv/src directory modes (narrower, but permission-inconsistent within
   `app_root`) vs. defer. **Chose the app-group addition** — same pattern as
   (1), explicitly flagging the future-secrets tradeoff rather than treating
   it as a non-issue (nothing sensitive is actually staged there yet — the
   secrets task is a stub, per DD-0014).

Both landed as two new `ansible/roles/base/tasks/main.yml` tasks
(`ansible.builtin.user` with `groups:`/`append: true`), each with an inline
comment recording the reasoning above and the fresh-SSH-session caveat
(standard Linux group-membership behavior — a change doesn't apply to an
already-open session). `ansible-playbook site.yml --syntax-check` clean
(`ansible-lint` isn't installed in this environment, unlike some earlier
SPEC-032 sessions).

**Full verification sequence, in order:**

1. `tools/ops/deploy.sh` (converge) — `__main__.py` fix — `deploy.sh` again
   — confirmed `python -m sask.cli --help` runs on the droplet.
2. Ansible permission fixes added — `deploy.sh` again (`changed=1` each,
   idempotent otherwise) — fresh `connect.sh` session — confirmed `dave` is
   in `sask sudo systemd-journal`; `logs query`, `convert`, `config check`
   all run directly as `dave`, no `sudo -u sask` impersonation needed.
   `logs query --unit sask` returned real production journal lines
   (gunicorn lifecycle + app JSON), same shape as TC-034-04's dev journal —
   confirming REQ-OPS-020's dev/prod parity claim end to end.
3. `tools/ops/acceptance-test.sh` — all 5 checks PASS.
4. `tools/ops/verify-logging.sh` — PASS, no regression from the ansible
   changes.
5. `tools/ops/redeploy.sh -y` — full destroy/recreate/deploy/acceptance
   cycle, confirming the whole thing (including both new permission-model
   tasks) survives a from-scratch droplet build, not just an in-place
   update: `ok=44 changed=38 failed=0`, automatic `acceptance-test.sh` at
   the end all PASS.
6. Re-verified on the freshly-recreated droplet: `logs query` and
   `verify-logging.sh` both clean; live traffic (background vulnerability
   scanners hitting `/js/config.js`, `/.env.example`, etc. — ordinary
   internet noise, not a sask-specific concern) visible in the journal with
   correct structured request-finished records, confirming the logging
   pipeline handles real, unplanned traffic correctly.

`docs/user_testing.md`'s SPEC-034 Results table updated: TC-034-06 now
PASS. `docs/console_log.txt` was not further appended for this droplet
work — evidence is this devlog entry plus the command transcripts above.

## 2026-07-09 — SPEC-034: local UAT passed (TC-034-01–05); droplet check pending deploy

Formal UAT recorded in `docs/user_testing.md` (SPEC-034 section,
TC-034-01 through TC-034-06). User ran TC-034-01 through TC-034-05 on the
dev host (transcript: `docs/console_log.txt`) — all PASS, no notes requiring
fixes. TC-034-06 (SSH to `sask-droplet`, run `sask logs query` against the
production journal, confirm identical behavior to the dev journal) is
correctly still PENDING — the CLI hasn't been deployed yet. `DD-0021` and
`SPEC-034` stay `"proposed"` until TC-034-06 closes out after the upcoming
deploy/redeploy round.

**Observation from the transcript, noted for a future iteration, not
actioned now:** piping Markdown-formatted CLI output (`sask help <topic>`)
through an external pager like `glow` already renders it richly in-terminal
with zero `sask` code changes (visible in `docs/console_log.txt` — the same
`getting-started` content shown plain, then `glow`-rendered with real tables
and styled headings). Recorded as Open Question 9 in
`design/analysis/saskan-app-alt-port/port-open-questions.md`: a possible
future refactor to have the CLI's own output use `rich` formatting directly
(already an installed transitive dependency of `typer`, so no new dependency
needed) rather than relying on the user piping through an external tool.
Explicitly deferred — the CLI's current plain `typer.echo()` output stands
for this round.

## 2026-07-09 — SPEC-034: CLI adapter implemented (pending manual UAT)

Third functional area of the `saskan-app-alt` port, sub-phase 2 of 2 (after
SPEC-033, which this depends on for `logs query`'s dev journal).

**Two pre-implementation analyses first, per SPEC-034's own ordering**, both
in `design/analysis/saskan-app-alt-port/` (extending, not replacing, the
existing `port-*.md` set — see that folder's `README.md` for the location
reasoning): `legacy-cli-deepening.md` separates reusable Typer idiom (the
required no-op root callback — the legacy project's own devlog records a
real bug from omitting it; paired long/short options with example-invocation
docstrings; `typer.Exit(code)`; a generalized `echo_dict` helper) from legacy
command logic that must not be ported (`connect.py`/`version.py` both bundle
domain logic directly into the command body, with no delegation to a
separate function — precisely DD-0021's "MOUTH not BRAIN" anti-pattern), and
recommends `typer.echo()` uniformly over the legacy project's inconsistent
`rich`/`typer.echo()` mix — so `sask` adds no `rich` dependency of its own
(it still arrives transitively via `typer`, confirmed at `poetry install`,
but nothing in `sask`'s own code imports it).
`tools-ops-vs-cli.md` classifies every `tools/` script against DD-0021's
boundary: all of `tools/ops/*`'s infra/deploy scripts stay ops;
`set-log-level.sh` stays ops as DD-0021's own named example (its
aspirational code comment about a future CLI command is now stale,
superseded by DD-0021's written decision — flagged for correction next time
that file is touched, not actioned here); `verify-logging.sh` is the one
real straddler, with a proposed (not actioned) future `logs verify` CLI
command as a follow-on; `tools/dev/` and `tools/helpers/` are named as a
third bucket outside DD-0021's scope entirely (host bootstrap / sask-unaware
utilities). No `tools/` file was edited, moved, or had logic ported —
recommend-only, per scope.

**`src/sask/cli/`** — a Typer consumer adapter, thin per DD-0021's clean-room
rule (parse → call the same clean-room engine/spine function the web adapter
calls → format output; no domain logic in any command body):

- `sask help [topic]` — reads the identical Markdown source
  `discover_topics()`/`index_path()` (`sask.help.loader`) resolve for the web
  `/help` route; one source, two adapters.
- `sask convert --pulse N` — calls `sask.calendar.pulse.pulse_info()`, the
  same function the web `/` route calls, returning the same `PulseInfo`
  fields (verified: `sask convert --pulse 0` prints `orbital_position: 0.0`,
  matching the `/?pulse=0` → `0.0000%` behavior `test_spec_005.py` already
  documents).
- `sask asset list` / `sask asset info <kind> <id>` — descriptor-only
  (DD-0016's split); the module never imports `fetch_payload` at all, so
  neither command can read a payload file even by accident (a structural
  guarantee, not just a runtime check).
- `sask config check` — runs the same `load_config()` `create_app()` calls,
  reports success with the identical count fields `config_loader`'s own
  "config loaded" log line carries, or the `ConfigError` message at exit 1 —
  never a raw traceback.
- `sask logs query [--level] [--since] [--grep] [--unit] [--user] [-n]` —
  wraps `journalctl`. The argv is built as a **list**
  (`_build_journalctl_argv`), never a shell string
  (`subprocess.run(argv, shell=False)`), so a `--grep` value containing
  shell metacharacters is inert — confirmed live:
  `sask logs query --grep '; echo INJECTED'` never executed the injected
  command (journalctl itself rejected the pattern; nothing was echoed).
  Verified end-to-end against the real SPEC-033 dev journal:
  `sask logs query --user --unit sask-dev -n 5` returned real gunicorn +
  app JSON lines from the running dev service.

**Layer purity**: a new AST-based test
(`test_engine_modules_import_no_cli`, mirroring `test_spec_005.py`/
`test_spec_032.py`'s Flask-free check) confirms `config_loader.py`,
`logsetup.py`, `message.py`, every `calendar/*.py`, and every `asset/*.py`
import no `sask.cli`. `cli/_paths.py` centralizes the repo-root walk-up (the
same depth as `web/__init__.py`, since `cli/` and `web/` are siblings) so no
`commands/*.py` file has to re-derive its own path-resolution depth — the
exact class of bug the SPEC-029 tools/ reorg hit when moved files sat one
directory level deeper than old math assumed.

**New dependency:** `typer >=0.12` (pulls in `rich` transitively for
Typer's own help rendering — not used directly by any `sask` code, per the
analysis's recommendation above). New console script: `sask = "sask.cli:main"`.

**Tests:** `tests/test_spec_034.py`, 35 tests — layer purity (parametrized),
help/convert/asset/config-check behavior (via `typer.testing.CliRunner` and
direct function calls), `logs query`'s argv-mapping and injection-safety
tests run without any live journal (per the spec's own guidance), a
structural check that no command name in `--help` output suggests service
mutation. Full suite: 745 passed (was 710). `bash tools/dev/pre-commit-check.sh`
clean (ruff lint/format, shellcheck, pymarkdown, validate_specs, the
validate_specs pytest suite).

**Manually exercised locally** (not yet the formal UAT): every command run
directly (`convert`, `asset list`/`info`, `config check`, `help`
index/topic, `logs query` against the real dev journal) plus each error path
(unknown asset, unknown help topic, invalid `--config-dir`) — all clean exits
and messages, no tracebacks.

**Not done in this pass, deliberately:** no `tools/ops/*` script was edited,
moved, or migrated (recommend-only this round, per SPEC-034 scope-out). No
SSH to the droplet to run `logs query` against the production journal —
that's SPEC-034's own `[manual]` UAT step. `design/decisions/dd-0021-cli-adapter.toml`
and `design/specs/spec-034-cli.toml` stay `"proposed"` until that manual UAT
is confirmed.

## 2026-07-09 — SPEC-033: dev/prod logging parity implemented (pending manual UAT)

Second functional area of the `saskan-app-alt` port, sub-phase 1 of 2 (SPEC-033
before SPEC-034 — the CLI's `logs query` command needs a dev journal to query).
Routing/docs only, no application code change, per REQ-OPS-020/SPEC-033 scope.

**New:** `tools/dev/sask-dev.service.template` — a systemd *user* unit modeled
on the production unit (`ansible/roles/runtime/templates/sask.service.j2`):
same `gunicorn wsgi:app --no-control-socket` invocation and no
`--access-logfile`/`--error-logfile` (so stdout/stderr flow to the user
journal exactly as prod's flow to the system journal via journald), but with
all production-only hardening (`ProtectSystem`, `ProtectHome`,
`NoNewPrivileges`, `PrivateTmp`) and the `EnvironmentFile=` dropped — dev runs
as the developer's own user with no `/etc/sask/environment`.
`tools/dev/sask-dev-service.sh` — one helper
(`install|enable|start|stop|restart|status|tail|logs`) that resolves the repo
root and venv path (`poetry env info --path`) into the template at install
time and writes it to `~/.config/systemd/user/sask-dev.service`.

**Linger investigated, not guessed:** systemd's documented behavior
(`systemd-logind(8)`) is that a user's `--user` instance stops when their last
session ends unless lingering is enabled (`loginctl enable-linger <user>`).
This is general systemd behavior, not something host-specific to empirically
discover. `install` checks and reports the current linger state rather than
changing it — enabling linger is a host/account-level change left to the
developer, consistent with not auto-running infra/session commands.

**Docs:** `docs/dev-setup.md` gained a new "## 6. Run the app as a dev
systemd service" section (existing "Run pre-commit checks" renumbered 6→7),
covering install/enable/start, log retrieval
(`journalctl --user -u sask-dev` or the helper's `logs`/`tail` subcommands),
the linger note, and when to prefer this over the existing direct-run path
(`tools/dev/start_web.sh`, unchanged).

No `tests/test_spec_033.py` was added — the spec's own acceptance criteria
scope this as infra/docs only, with no application code change to test.

## 2026-07-09 — SPEC-033 accepted: dev systemd service verified by user

User ran `install`/`enable`/`start` and confirmed via `journalctl --user -u
sask-dev` (transcript: `docs/console_log.txt`): the unit installs and starts
cleanly (`Started sask-dev.service`), gunicorn's own plain-text startup lines
(`Starting gunicorn 26.0.0`, `Listening at: http://127.0.0.1:8000`, `Booting
worker`) and the app's structured JSON (`{"timestamp": ..., "level": "INFO",
"logger": "sask.config_loader", "message": "config loaded", "bodies": 15,
"stars": 16, ...}`) both land in the user journal, coexisting exactly the way
SPEC-032's prod journal already does — confirming dev/prod parity structurally,
not just by inspection. Lingering is not enabled for the account (expected,
`install`'s own check reported this); the service will stop at logout unless
`loginctl enable-linger` is run, which remains the developer's call. Setting
`SPEC-033` to `status = "accepted"` (`REQ-OPS-020` has no `status` field, same
as other reqs). Next: SPEC-034, the CLI adapter itself, now unblocked.

## 2026-07-08 — SPEC-032 accepted: full redeploy verified, DD-0020/SPEC-032 → accepted

Ran `tools/ops/redeploy.sh -y` (full destroy/recreate/deploy/acceptance
cycle, not just a converge) to confirm the logging port survives a
from-scratch droplet build, not just an in-place update: OpenTofu
recreated the droplet + firewall + reserved-IP assignment, the one-time
root bootstrap ran, then the full `site.yml` play — `ok=42 changed=36
failed=0`. `acceptance-test.sh` (run automatically at the end of
`redeploy.sh`) — all 5 checks pass.

`verify-logging.sh` re-run against the fresh droplet: `total=50
json_ok=16 secret_hits=0`; journald drop-in present with both caps;
8.0M disk usage, well under the 200M cap. Also grepped the full `sask`
unit journal for "error"/"permission denied" — zero matches (confirms the
control-socket fix from the prior entry holds on a clean build, not just
the box it was first fixed on). User independently ran `verify-logging.sh`
and manually browsed `journalctl` for `sask` entries themselves, seeing
both the app's structured records and the systemd/gunicorn lifecycle
lines, no issues.

Both the in-place `deploy.sh` path and the full `redeploy.sh` path are now
verified against a live droplet, satisfying SPEC-032 acceptance criterion
7. Setting DD-0020 and SPEC-032 to `status = "accepted"`
(REQ-OPS-019/REQ-SEC-004 have no `status` field in the reqs schema — only
`decisions` and `specs` carry one).

## 2026-07-08 — SPEC-032 live deploy: gunicorn control-socket fix + verify-logging.sh over-strictness fix

First live deploy of the SPEC-032 logging port (`tools/ops/deploy.sh`
converging the existing droplet, not a full rebuild). Two real issues
surfaced, both investigated and fixed before re-deploying — not dismissed
as noise.

**Issue 1 — gunicorn 26.0.0 control-socket permission error.** First
`verify-logging.sh` run failed (`bad_json=42/50`). `journalctl -u sask -o
cat -n 50` showed `[ERROR] Control server error: [Errno 13] Permission
denied: '/home/sask'` on every gunicorn start, plus gunicorn's own
plain-text startup lines ("Starting gunicorn", "Listening at:", "Using
worker:", "Booting worker with pid:") interleaved with the app's JSON.
`gunicorn --help` confirmed: 26.0.0 added a control socket defaulting
under the user's home dir; `ProtectSystem=strict`/`ProtectHome=true`
(already in the unit, intentional hardening) correctly blocks it, and
`app_user=sask` has no real home dir anyway (`create_home: false`). Non-
fatal — the app served every request correctly throughout
(`acceptance-test.sh` passed both before and after) — but newly *visible*
now that `--error-logfile` no longer swallows gunicorn's own stderr into
an unread file. Confirmed via `sudo systemctl status sask` that the
crash-loop entries also visible in that journal window (`203/EXEC`,
several restart cycles) were old history from 2026-07-01, unrelated to
this deploy — the service was `active (running)` throughout.

Fix: added `--no-control-socket` to `sask.service.j2`'s `ExecStart` (a
real gunicorn flag, confirmed via `gunicorn --help`, not guessed) — this
service doesn't use the control interface, so disable it rather than
carve a `ProtectHome` exception for an unused feature. Re-deployed;
confirmed the error is gone and the app still serves correctly.

**Issue 2 — `verify-logging.sh` was checking the wrong thing.** Its
original check demanded *every* line under the unit be valid JSON, which
is wrong: SPEC-032's own `deploy_wiring` text already says gunicorn's own
operational notices legitimately flow to journald as plain text — only
the app's own request-level records need to be structured JSON. Changed
the check from "zero non-JSON lines" to "at least one well-formed app
JSON line, and zero cleartext secrets across all lines regardless of
format" — the actual acceptance-criterion-7 bar, not an accidentally
stricter one.

**Live results after both fixes, on the existing (not recreated)
droplet:**

- `tools/ops/deploy.sh` — `failed=0`.
- `tools/ops/acceptance-test.sh` — all 5 checks pass.
- `tools/ops/verify-logging.sh` — `total=50 json_ok=16 secret_hits=0`;
  journald drop-in present with both caps; disk usage 8.0M (well under
  the 200M cap).
- `tools/ops/set-log-level.sh DEBUG` then `INFO` — both converged cleanly
  (`--tags runtime` correctly scoped to just that role), the environment
  file updated each time, confirmed via a live request that the service
  kept serving throughout, then set back to `INFO` for production.

**Still to do:** `tools/ops/redeploy.sh -y` (full destroy/recreate cycle)
to confirm the whole thing survives a from-scratch build, then flip
DD-0020/SPEC-032 to `"accepted"`.

## 2026-07-08 — SPEC-032 Phase 4: deploy wiring (not yet live-verified)

Fourth commit of the SPEC-032 logging port — the deploy-side half. No
Python changes; Ansible, ops scripts, and docs only.

**Found and fixed a real pre-existing conflict:**
`ansible/roles/runtime/templates/sask.service.j2` was already running
gunicorn with `--access-logfile {{ log_dir }}/access.log
--error-logfile {{ log_dir }}/error.log` — i.e. writing its own log files,
bypassing journald entirely, directly conflicting with REQ-OPS-019.
Removed both flags (gunicorn reverts to its stdout/stderr defaults, both
journald-captured under systemd); also dropped the now-unneeded
`ReadWritePaths={{ log_dir }}` hardening line. `log_dir` itself is left in
place — it's one of REQ-OPS-015's three standing platform directories,
unrelated to this spec, just no longer written into by sask.

**Journald caps:** new `roles/base/templates/journald-sask.conf.j2`
(`SystemMaxUse=200M`, `MaxRetentionSec=14day` — new `group_vars/all.yml`
vars `sask_journald_system_max_use`/`sask_journald_max_retention`),
templated to `/etc/systemd/journald.conf.d/sask.conf` by a new `base` role
task, restarting `systemd-journald` on change.

**SASK_LOG_LEVEL:** added to `roles/runtime/templates/environment.j2`,
sourced from a new `sask_log_level: INFO` group_vars default.

**Two new ops scripts** (`tools/ops/`):

- `set-log-level.sh <LEVEL>` — validates the level name, then runs
  `ansible-playbook site.yml --tags runtime -e sask_log_level=<LEVEL>`
  (new `runtime` tag added to `site.yml`'s role list) and restarts the
  service. Ansible-driven rather than a direct SSH+sed edit, per
  discussion: keeps Ansible the single source of truth, so a later plain
  `deploy.sh` run doesn't silently revert a hand-edited environment file.
  Written as a standalone script (not inline Ansible) so it can be called
  the same way once the CLI's log-level command exists.
- `verify-logging.sh` — automates SPEC-032 acceptance criterion 7:
  SSHes to the droplet (read-only) and (1) validates recent
  `journalctl -u sask -o cat` lines are well-formed JSON with the expected
  keys and scans for cleartext `DIGITALOCEAN_TOKEN`/`dop_v1_` occurrences,
  failing on either; (2) confirms the journald drop-in exists with both
  caps set; (3) prints `journalctl --disk-usage` informationally. Only
  needs `sudo` for the `journalctl` read (matches the pattern already in
  the runbook — passwordless sudo per DD-0019/REQ-SEC-003).

**Docs:** new "Logging" section in `docs/deploy-runbook.md` — raw/follow
journalctl commands, `verify-logging.sh`, `set-log-level.sh`.

**Verification done this round:** `ansible-playbook site.yml
--syntax-check` passes; manually rendered the three touched/new templates
with `group_vars/all.yml` via Jinja2 directly to confirm the new lines
(`SASK_LOG_LEVEL=INFO`, the journald caps, the trimmed `ExecStart`) render
correctly; `shellcheck -S warning` clean on both new scripts; full
`pre-commit-check.sh` green; full Python suite still 710 passed (no
Python touched this phase).

**Not done — needs a live droplet and your go-ahead:** actually deploying
this (`redeploy.sh` or `deploy.sh`), then running `verify-logging.sh`
against the real box to satisfy acceptance criterion 7. DD-0020 and
SPEC-032 stay `status = "proposed"` until that live check passes — flipping
them to `"accepted"` now would be claiming a criterion that hasn't
actually been exercised yet.

## 2026-07-08 — SPEC-032 Phase 3: web adapter — request-context binding

Third commit of the SPEC-032 logging port. `src/sask/web/__init__.py`
`create_app()`:

- Calls `logsetup.configure()` as its first line — before `Flask(__name__,
  ...)` is instantiated, so `"sask"` already has its stdout handler
  installed by the time Flask's own `app.logger` (a child logger, since
  `app.name` == `"sask.web"`) is first touched. This means Flask's own
  automatic unhandled-exception logging (`app.logger.error(...,
  exc_info=...)`, built into `handle_exception`) lands on our JSON handler
  for free, rather than Flask installing its own default stderr handler.
- Wraps `load_config()` in try/except `ConfigError`: logs CRITICAL
  ("config load failed; app cannot serve") then re-raises — the process
  still exits, but the failure is on record first.
- `before_request`/`after_request`/`teardown_request` hooks: bind a
  per-request `request_id` (uuid4 hex) + method + path via
  `logsetup.bind_context()`; log one INFO "request finished" record
  (status, duration_s) in `after_request`; unbind in `teardown_request` so
  context never leaks into the next request on the same worker.

Manually verified against a live `create_app()`/test-client run before
writing formal tests — confirmed: a normal request's "request finished"
line and an engine outcome line (e.g. an asset-catalog-miss on a 404)
share one `request_id`; a genuinely unhandled exception produces exactly
one ERROR line (Flask's own, via `app.logger`) carrying the full
traceback and the bound request context — not a second, redundant
error log from anywhere else.

**Bug found and fixed while writing Phase 3's end-to-end tests:**
`_make_logger_with_buffer()` (Phase 1/2 test helper) mutates real, cached
logger singletons directly (e.g. `logging.getLogger("sask.config_loader")`
— the exact object `config_loader.py` logs through) and never restored
`propagate`/handlers afterward. Once any Phase 2 test ran, later
end-to-end tests relying on propagation up to `"sask"`'s real handler
silently lost records to an abandoned per-test buffer. Fixed by having the
autouse fixture blank-slate every `"sask"`/`"sask.*"` logger (handlers
cleared, `propagate=True`, level `NOTSET`) before and after each test —
full isolation regardless of run order, not just for the specific loggers
one test happens to touch.

**Tests:** `tests/test_spec_032.py` grew to 41 cases — 6 new end-to-end
adapter tests using `capsys` against real stdout (since `configure()`
targets `sys.stdout` by default, not an injectable stream, when invoked
via `create_app()`): config-load context-freedom, CRITICAL-and-reraise on
`ConfigError`, request-finished shape, engine/adapter request-id
correlation on a 404, single-ERROR-with-context on an unhandled exception,
and no context leakage across two sequential requests. Full suite: 710
passed. `pre-commit-check.sh`: all green.

**Scope note:** the app now actually emits structured JSON to stdout at
runtime (verified manually against a real `poetry run` process). Deploy
wiring — gunicorn-to-journald, journald caps, `SASK_LOG_LEVEL` in the
Ansible environment template, the log-level-change and log-verification
ops scripts — is Phase 4.

## 2026-07-08 — SPEC-032 Phase 2: engine-layer log instrumentation

Second commit of the SPEC-032 logging port. Instruments the three engine
call sites DD-0020's starter set names, all context-free (`get_logger`
only, no request/transport awareness):

- `config_loader.load_config()` — one INFO record on success with counts
  (bodies, stars, houses, comets, lunar_calendars, sky_styles,
  lore_calendars, assets). No CRITICAL-on-`ConfigError` here by design —
  SPEC-032 places that at the `create_app()` boundary (Phase 3), so a
  config failure is logged once, not at every layer it bubbles through.
- `calendar/ephemeris.py get_sky_series()` — one INFO record per completed
  request (`step_count`, `duration_s`); WARNING instead of INFO once
  duration reaches 4.5s (near/at the ~5s soft budget from REQ-OPS-010 /
  `tools/ops/perf_config.py BUDGETS["ephemeris_worst_case_s"]`). No
  per-record logging added — DD-0020 marks it optional and there's no
  caller need yet.
- `asset/retrieval.py` — `fetch_payload()` logs "asset served" (kind, id,
  size) at INFO on success; `resolve_descriptor()` and `fetch_payload()`
  each independently log "asset catalog miss" at INFO (never
  WARNING/ERROR, per the rubric's explicit not-found note) since each is
  an independently callable lookup — in the normal routes.py call
  sequence only one of the two ever actually fires per request.

Also fixed a latent gap in Phase 1's `logsetup.reset()`: it cleared
handlers but never restored `propagate`, so after any `configure()` call
the `"sask"` logger stayed non-propagating for the rest of the process.
Not hit by Phase 1's own tests, but caught while wiring Phase 2's tests.

**Tests:** `tests/test_spec_032.py` grew to 35 cases — added config-load
counts, ephemeris INFO/WARNING level selection (WARNING case verified via
a monkeypatched `time.perf_counter`, no real 4.5s sleep), asset
served/miss outcomes at the correct level, and a layer-purity AST check
(mirroring the existing Flask-free engine test) confirming
`config_loader.py`, all of `calendar/*.py`, and all of `asset/*.py` import
neither `flask` nor `sask.web`. Full suite: 704 passed. `pre-commit-check.sh`:
all green.

**Scope note:** engine only — nothing calls `logsetup.configure()` yet, so
none of this actually reaches stdout in the running app until Phase 3
wires the adapter.

## 2026-07-08 — SPEC-032 Phase 1: structured-logging spine module

First commit of the SPEC-032 logging port (DD-0020, REQ-OPS-019,
REQ-SEC-004). Adds `src/sask/logsetup.py`, the shared-spine facility the
rest of the port builds on:

- `JsonFormatter` — one structured JSON object per stdout line (timestamp,
  level, logger, message, bound context, extra fields, exception text).
- `TRACE` level registered below `DEBUG`, with a guarded `Logger.trace()`
  so per-record firehose logging (e.g. ephemeris) costs nothing when off.
- `LevelRangeFilter` — a reusable [min, max] level gate.
- `bind_context()`/`reset_context()`/`current_context()` — `contextvars`-based
  per-request field binding, for the web adapter to use in Phase 3.
- `redact_fields()` (REQ-SEC-004) — scrubs fields whose key matches a
  documented, extensible marker set (`token`, `password`, `secret`, ...),
  recursing into nested dicts, plus scrubs known secret env-var values
  (starting with `DIGITALOCEAN_TOKEN`) wherever they appear in message
  text or string fields.
- `configure()` — idempotent, installs the JSON handler on the `"sask"`
  logger once; reads `SASK_LOG_LEVEL` (default `INFO`). Not yet called
  from `create_app()` — that's Phase 3.
- `reset()` — test-support only, un-configures between test cases.

No new dependency: implemented on stdlib `logging`/`contextvars`, per
`pyproject.toml`'s no-new-deps-without-permission rule.

**Tests:** `tests/test_spec_032.py`, 15 cases — formatter shape, TRACE
gating, level-range filtering, context binding/leak safety, redaction
(key-based, extensible, env-value, nested), `configure()` idempotency and
env-level resolution. Full suite: 684 passed. `pre-commit-check.sh`: all
green.

**Scope note:** this commit is the spine only — no engine or adapter code
logs anything yet (Phase 2/3), and no deploy wiring yet (Phase 4).

## 2026-07-02 — fix: /help never actually deployed live (SPEC-030 gap, not a port bug)

User manual browser testing found `/help` on production rendering the page
shell with no intro text and no topic links, while working correctly on
`http://127.0.0.1:5000/help` locally.

**Root cause, confirmed - a pre-existing SPEC-030 gap, unrelated to the
DD-0019 Ubuntu/Poetry port:** `src/sask/help/loader.py`'s `discover_topics()`
scans `docs/help/` for Markdown files at `create_app()` time.
`src/sask/web/__init__.py` resolves that path via the same file-relative
walk-up as `config_dir`. Locally, `docs/help/` is just there in the full git
checkout, so it works. On production, `ansible/roles/app/tasks/main.yml`
only ever synced `src/sask/`, `config/`, `assets/<version>/`, and `wsgi.py`
to `/opt/sask/` - never `docs/help/`. `SPEC-030`'s own addendum said this
plainly: *"No live redeploy in this spec... deploying the help guide live is
a separate, later action."* That action was never done - not by this
session's deploy-pipeline work, and not before it either. The help feature
has never worked on any production droplet since it was built (2026-06-25).

**Fix:** added `app_help_dir` (`app_root/docs/help`) to
`ansible/group_vars/all.yml`, and a new sync task in the `app` role -
parent-dir-then-`synchronize`, same pattern as `config/`/`assets/`,
notifying a service restart (the topic map is built once at startup per
DD-0018's `render_timing`, so a new/removed topic file needs one).

Verified live: `deploy.sh` re-run showed the two new tasks as `changed`;
`/help` now shows the intro paragraph and both starter topics
(`getting-started`, `calendar-lore`); `/help/getting-started` renders its
table and code block correctly. Acceptance suite still green. SPEC-030's
addendum carries a RESOLVED note with the full detail.

## 2026-07-01 — Full deploy/redeploy/perf validation on rebuilt Ubuntu dev host; ephemeris budget accept-and-documented

First live exercise of the deploy harness (REQ-OPS-013) and the remote
perf procedure (REQ-OPS-016/SPEC-025) since the DD-0019 Ubuntu/Poetry port,
plus two more port gaps found and fixed along the way.

**Pre-flight:** local Tofu state was empty (never migrated off the old
NixOS VM) while the real droplet, reserved IP, firewall, SSH key, and DNS
record were still live in DigitalOcean - an orphaned-from-state situation
DD-0014 explicitly names as a risk of local-only state. Reconciled via
`tofu import` (6 resources); `tofu plan` showed drift on `image` (slug vs.
the numeric ID DO's API returns) and `ssh_keys` (not persisted on droplet
reads) - both known import artifacts of the DO provider, harmless for the
immediate next step since `tofu destroy` acts on state IDs, not config
diff. `tofu plan -destroy` confirmed exactly the 6 real resources and
nothing else before anything was touched.

**Two more DD-0019 port gaps found (same shape as the ansible gap from the
audit earlier today - a tool the retired `flake.nix` devShell provided
directly, dropped without a replacement):**

1. `xcaddy` (+ `go`) - builds the custom Caddy binary with the rate-limit
   plugin, run locally by the `caddy` Ansible role (`delegate_to:
   localhost`). Not packaged in apt; fixed via `golang-go` added to
   `init-dev-host.sh`'s apt list plus a new `go install
   github.com/caddyserver/xcaddy/cmd/xcaddy@latest` step (with the
   `~/go/bin` PATH addition persisted to `.bashrc`, matching the
   pyenv/poetry installers' own convention).
2. `tools/ops/deploy.sh`'s SSH-readiness wait loop hardcoded `-o
   User=root`, so it always timed out on a droplet where an earlier
   partial run had already gotten as far as the base role's `PermitRootLogin
   no` (i.e., any re-run after a failure past that point, not just a fresh
   droplet). Fixed to accept either root or dave.

**Full cycle executed and verified, in order:**

- `destroy.sh -y` - clean teardown of the real live stack (6 resources),
  confirmed via `doctl` and DNS no longer resolving.
- `provision.sh -y` - clean rebuild from zero (`7 added, 0 changed, 0
  destroyed`), new reserved IP `46.101.68.21` (droplet `581640609`).
- `deploy.sh` - failed first attempt at the Caddy build step (xcaddy gap
  above); after the fix, re-run resumed cleanly. A second consecutive run
  reported `ok=32 changed=0 failed=0` - REQ-OPS-013's idempotency bar met
  for real.
- `acceptance-test.sh` - all 5 checks pass; independently confirmed via
  browser (including asset retrieval).
- `redeploy.sh -y` - the full single-mainline-act cycle: droplet
  recreated (`581640609` -> `581645959`) with the reserved IP held
  unchanged at `46.101.68.21`, confirming REQ-OPS-013's DNS/SSH-alias
  survival guarantee. Deploy + acceptance both auto-ran and passed on the
  first try (both gaps already fixed by this point).

**Performance validation (REQ-OPS-010/016):**

- Local Layer 1 (pytest-benchmark, 20 hot paths) and Layer 2 (local
  gunicorn + `perf_http.py`) both saved; all budgets pass on this dev host
  (interactive ~0.5-1.4 ms, worst-case ephemeris download 4.19-4.28 s
  against the 3-5 s budget).
- Remote (`perf-remote.sh`, against droplet `581645959`): interactive
  pages pass comfortably (~120-135 ms vs. 500 ms budget). Worst-case
  ephemeris download genuinely breaches: 9.731 s (scribal) / 8.808 s
  (kinematic) vs. the 3-5 s budget. On-droplet engine timing shows a
  uniform ~2.0-2.6x slowdown vs. the dev host across every single hot
  path (e.g. `get_sky_series_30day_5min`: 6924 ms remote vs. 3042 ms
  local) - raw per-core compute cost on the $6/mo `s-1vcpu-1gb` droplet,
  not redundant/cacheable recompute. Full results: `tests/results/perf/
  REMOTE-2026-07-01.md`.

**Decision: accept-and-document (per DD-0015's rubric).** User confirmed
this exact call was reached once before but never recorded clearly enough
to stick, causing the same question to resurface - DD-0015 and
REQ-OPS-010 have both been updated with explicit RESOLVED notes so this
doesn't happen a third time. No cache, no CPU-Optimized droplet resize -
the added DigitalOcean spend isn't justified at this scale. DD-0015 moved
from `proposed` to `accepted`.

## 2026-07-01 — DD-0019 port audit: found ansible gap + 3 more `.venv` bugs

Pre-flight audit ahead of next session's full deploy/redeploy + perf-test
validation: asked "what did the NixOS->Ubuntu/Poetry port (DD-0019/
SPEC-031) miss?" Found one real blocker and a class of repeat bug.

**Blocker:** `ansible-playbook` was not installed anywhere on the dev host.
The retired `flake.nix` devShell provided `pkgs.ansible` + `pkgs.ansible-lint`
directly; the port dropped both without a replacement. `deploy.sh` and
`redeploy.sh` both shell out to bare `ansible-playbook` — completely
blocked. Fixed: added `ansible` + `rsync` (also previously undeclared,
though already present) to `tools/dev/init-dev-host.sh`'s `APT_ESSENTIALS`
and `docs/dev-setup.md`. Installed on this host; verified `ansible-playbook
--version`, `ansible.posix` collection present, and `ansible-playbook
site.yml --syntax-check` all pass with no live changes made.

**Same `.venv/bin/...` bug as start_web.sh, in 3 more scripts:** confirmed
broken by direct run, fixed to `poetry run`:

- `tools/dev/run-tests.sh` (the general test runner)
- `tools/ops/run_perf.sh` (local perf-benchmark baseline — the exact script
  next session's "run performance tests locally" step depends on)
- `tools/ops/perf-remote.sh`'s two *local* invocations (its remote
  `/opt/sask/.venv/bin/python3` path was already correct — Ansible really
  does create a plain `.venv` on the droplet via `ansible.builtin.pip`,
  unrelated to the dev host's Poetry setup)

Also fixed matching usage-docstrings in `perf_engine.py`/`perf_http.py`,
and stale "sask-dev VM / nix develop" headers in `deploy-runbook.md`,
`provision.sh`, `destroy.sh`, `recreate-droplet.sh`, `perf-remote.sh`, and
`docs/references.md`'s toolchain list (NixOS/Nix flakes -> Ubuntu/pyenv).

**Confirmed NOT a gotcha:** the dev-host Python 3.12 pin exists because
Werkzeug/gunicorn aren't validated on Ubuntu 26.04's default 3.14 — but
the production droplet image is pinned to `ubuntu-24-04-x64`
(`infra/tofu/variables.tf`), which ships 3.12 natively. No mismatch today;
worth a DD note if `droplet_image` is ever bumped, but not urgent.

Verified end-to-end: `run-tests.sh` (669 passed), `run_perf.sh` (20
benchmarks passed), `ansible-playbook --syntax-check` (clean). Also found
and fixed a bug in my own `test_make_tree.py` from the prior entry: the
unhappy-path PATH-stripping accidentally removed `bash`'s own directory.

## 2026-07-01 — `tools/helpers/` housekeeping: reviewed, fixed, tested

Reviewed the 5 scripts in `tools/helpers/` (imported from another project,
unused so far) for readability/flexibility and added unit tests (31 tests,
happy + unhappy path each).

**Found `host_info.py` and `validate_json.py` were unrunnable as committed:**
they import `psutil` and `jsonschema`, neither declared in `pyproject.toml`.
Added both to the `dev` dependency group and relocked (user-authorized,
following the same "eyes wide open" standard as the DD-0019 port relocks).

**Minor refactors:**

- `host_info.py`: `sys_info()` now returns a `dict` instead of a
  pre-serialized JSON string; `__main__` does the `json.dumps()` for CLI
  output. More flexible for callers wanting structured data.
- `make_tree.sh`: added a `command -v tree` guard with a friendly error —
  the script depended on `tree` but nothing installed it. Since the user
  wants to keep this script working, added `tree` to
  `tools/dev/init-dev-host.sh`'s `APT_ESSENTIALS` and to
  `docs/dev-setup.md`'s reference list, and installed it on this host.
  `tree.txt` output added to `.gitignore`.
- `validate_json.py`: missing/malformed input files now print a one-line
  stderr message and exit 2, instead of a raw traceback.
- `match_semver.py`, `stamps.py`: no changes needed.

Full suite: 669 passed (638 prior + 31 new). Pre-commit clean.

## 2026-07-01 — fix `tools/dev/start_web.sh` for Poetry (post DD-0019 port)

`start_web.sh` was never updated when the dev host moved off NixOS: it called
`.venv/bin/flask` directly, but Poetry here creates the venv out-of-project
(`~/.cache/pypoetry/virtualenvs/...`), not in a repo-local `.venv/`, so the
script failed with "No such file or directory". Header comments also still
referenced the retired `sask-dev` VM. Fixed to `poetry run flask --app
sask.web run` and updated the SSH-tunnel comment to `ubuvm`. Verified
end-to-end: `ssh -L 5000:localhost:5000 ubuvm` -> `cd ~/code/sask` -> `bash
tools/dev/start_web.sh` -> `curl localhost:5000/health` returns 200; user
confirmed working via manual smoke test.

## 2026-06-30 — DD-0019/SPEC-031: de-NixOS port complete; dev host now Ubuntu 26.04 LTS + Poetry

Retired the NixOS `sask-dev` VM as the canonical dev environment and ported
sask to a stock Ubuntu 26.04 LTS host using pyenv + Poetry + empirically-derived
apt prerequisites. Full rationale in DD-0019. Key decisions and findings:

**Python pin:** System python3 on Ubuntu 26.04 is 3.14.4 — too new (Werkzeug +
gunicorn 3.14 support not yet validated). Pinned 3.12 via pyenv (3.12.13, latest
patch at time of port). pyproject.toml's python constraint tightened from `^3.12`
(caret, admits 3.13/3.14) to `~3.12` (tilde, 3.12-only). This was the only
change to pyproject.toml in scope per SPEC-031; `pymarkdownlnt` was added
separately as a dev dep to replace the NixOS-era manually-managed venv tool, with
explicit user authorization (see below).

**poetry.lock regenerated (twice, with authorization):** SPEC-031 originally said
"do not regenerate the lockfile." The first regen was unavoidable — the
`python-versions` constraint change invalidated the content-hash. User explicitly
authorized overriding the no-relock instruction. Diff confirmed metadata-only
(generator version, constraint string, content-hash — zero package version
changes). A second regen added `pymarkdownlnt` to the lockfile; similarly
metadata-minimal for existing packages. Both overrides recorded here per the
"eyes wide open" standard.

**System prereq list (empirically derived):** The apt prerequisites installed by
`tools/dev/init-dev-host.sh` were derived by cross-checking against
`infra/configuration.nix` (retired NixOS dev-VM config, kept in
`infra/archive/` as a reference) and confirmed on the new host. Native watch-items
explicitly checked: `import sqlite3, ssl, hashlib` passes — libsqlite3 and libssl
were present (Ubuntu build-essential / libssl-dev already shipped in the VM image).
Full apt list: pyenv build deps (build-essential libssl-dev zlib1g-dev libbz2-dev
libreadline-dev libsqlite3-dev libncursesw5-dev xz-utils tk-dev libxml2-dev
libxmlsec1-dev libffi-dev liblzma-dev) + essentials (git curl wget ca-certificates
openssh-client shellcheck).

**Verification results:**

- `poetry install` — 22 installs, clean.
- `poetry run pytest -q` — 638 passed (626 prior SPEC-027 + 12 new SPEC-030 = 638; no regression).
- `GET /health` — HTTP 200 from locally-started Flask server.
- `verify-do-secrets.sh` — all 4 checks pass against real secrets on the new host:
  infra.env present, DIGITALOCEAN_TOKEN format correct, DO API HTTP 200,
  SSH to sask-droplet succeeds.
- `verify-clean-env.sh` — written; to be run by user as part of UAT.

**Tofu state not yet migrated (known gap):** The local `terraform.tfstate` from the
retired NixOS VM has not been copied to the new host. `tofu init` has not been run
here. SPEC-031 acceptance criterion #7 calls for a read-only `tofu plan`; the
underlying token and SSH access are confirmed (DO API + SSH probe both pass), but
the `tofu plan` itself cannot be run without migrating state. Noted as a
follow-up: copy `terraform.tfstate` from the old VM and run `tofu init -upgrade`
to confirm provider downloads succeed on the new host.

**NixOS artifacts retired:**

- `flake.nix`, `flake.lock` — removed (git rm).
- `infra/configuration.nix` → `infra/archive/configuration.nix` (moved; historical
  reference only).
- `docs/vm-setup.md` — kept intact as history; superseded by `docs/dev-setup.md`.
- `CLAUDE.md` — NixOS / nix-develop / .venv references removed; Ubuntu/Poetry env
  documented.
- `tools/dev/pre-commit-check.sh` — `nix develop --command` wrappers removed; now
  uses `poetry run ruff`, `shellcheck` (on PATH via apt), `poetry run pymarkdown`,
  `poetry run pytest`.

**New tools deliverables (SPEC-031):**

- `tools/dev/init-dev-host.sh` — config-driven bootstrap: apt, OpenTofu (snap),
  pyenv, Python 3.12, Poetry. Secret-free; idempotent; shellcheck-clean.
- `tools/dev/verify-do-secrets.sh` — read-only DO token + SSH probe verifier.
- `tools/dev/verify-clean-env.sh` — re-runnable clean-environment verifier
  (SPEC-031 centerpiece): pyenv + 3.12 pin, native stdlib watch-items, poetry
  install, full suite, app boot + GET /health.

SPEC-031 status set to "accepted" on this entry's merge.

## 2026-06-30 — fix(ops): SSH readiness race in deploy pipeline

Diagnosed and fixed a deployment failure caused by a known gap (flagged in
the SPEC-029 addendum but deferred). `deploy.sh` was invoking Ansible
immediately after `tofu apply` without waiting for the new droplet's SSH
daemon to be ready, causing a transient connection-refused failure.

Added a 120 s retry loop (5 s intervals, polling root SSH) to `deploy.sh`
before the Ansible bootstrap check. Succeeds immediately on already-running
droplets — no overhead on normal re-convergence runs.

The incident also destroyed the production droplet and reserved IP (the
full `destroy.sh` path was used in recovery, which tears down all resources
including the `local_file` that writes `~/.ssh/config.d/sask`). Site was
restored via `provision.sh` from scratch (new reserved IP `68.183.242.7`,
DNS auto-updated) followed by `deploy.sh`. All five acceptance checks pass.

Lesson noted: redeploy pipeline should be included in acceptance testing
for any change, not treated as out-of-scope unless code touches deploy files.

## 2026-06-25 — DD-0018/SPEC-030: help guide implemented; accepted

**Phase D of the cleanup/elevation sequence.** Added a minimal help
guide: Markdown source under `docs/help/`, a thin Flask-free loader
(`src/sask/help/loader.py` — a third functional-area subpackage alongside
`calendar/` and `asset/`, matching DD-0017's package=noun/module=verb
convention and kept adapter-neutral for a future CLI), and two routes
under the existing web adapter.

**`discover_topics(help_dir)`** scans `docs/help/*.md` once at
`create_app()` time into a `{stem: resolved_path}` map, deliberately
excluding the `index` stem so `index.md` is never reachable at
`/help/index` and never listed as a topic — it's rendered as intro prose
above the topic list instead, via a separate `index_path()` lookup.
**`render_markdown(path)`** reads fresh and renders per request (no
caching), reused identically for both topics and the index intro — one
render code path, not two. Topic resolution in `routes.py` is a plain
dict `.get()` against the startup-built map; structurally impossible to
path-traverse since the URL value is only ever used as a dict key.

**`GET /help`** lists the discovered topics with the rendered intro above
them; **`GET /help/<topic>`** renders that topic wrapped in `base.html`,
or a "Topic not found" message wrapped in `base.html` with HTTP 404 (kept
in `base.html`, unlike the asset route's plain-text 404, since help pages
are always HTML and the whole point is feeling native to the app). One
"Help" nav link added. Starter skeleton: `index.md` (welcome) +
`getting-started.md` (one topic exercising headings, a fenced code
block, and a table — all three configured Markdown extensions:
`fenced_code`, `tables`, `toc`).

Added `markdown` (Python-Markdown) as a new runtime dependency —
pyproject.toml, regenerated `poetry.lock`, re-exported `requirements.txt`,
and `.venv/bin/pip install`'d to match how flask/gunicorn are both
poetry-declared and directly pip-installed in this project's
non-poetry-managed `.venv`.

`tests/test_spec_030.py` adds 12 tests (topic discovery and index
exclusion, render-extension checks, layer-purity, the two routes' HTML
behavior including the 404 case, and a direct check that
traversal-style values are never resolvable keys) — full suite now 638
(was 626), zero regressions. Manually verified locally via
`tools/dev/start_web.sh`: `/help` and `/help/getting-started` both render
correctly with nav, intro, table, and code block present.

No live redeploy — out of scope for this spec's acceptance criteria
(local verification is the bar); deploying the help guide live is a
separate, later action.

**DD-0018 and SPEC-030 flipped from `proposed` to `accepted`.**

## 2026-06-25 — Ephemeris export-time-estimate feature withdrawn

**Dropping the deferred ephemeris export-time/payload-size estimate UX
feature entirely — it will not be built.** This was the "accept-and-
document" outcome's proposed UX mitigation from DD-0015's rubric (see the
2026-06-22 entry below: "DD-0015 rubric outcome: raw per-core compute"),
parked as a still-unscoped, not-yet-requested followup pending a decision
that has now been made: don't pursue it.

Marked as withdrawn (one-line notes added, surrounding context left
intact — no history rewritten) in every design doc that named it:
`design/decisions/dd-0015-remote-performance.toml` (the rubric's
within-budget bullet, the accept-and-document bullet, and the
`followups` entry), and `design/specs/spec-025-remote-performance.toml`
(the `evaluation` deliverable's "on confirm" note). `design/reqs/
req-ops-010.toml` had no literal export-time-estimate text to mark, but
carried an anticipated "budget-text revision" tied to this feature
(per the 2026-06-22 devlog entry); added a `notes` field recording that
the revision is now moot and the existing budget text is unaffected and
accurate as written.

No code touched (none existed to remove — the feature was never built).
No other design decision changed. Past devlog entries left untouched.

## 2026-06-25 — SPEC-029 accepted: live redeploy verified

**`tools/ops/redeploy.sh -y` run live against the production droplet** to
verify the tool-path moves didn't break the deploy harness. The
infrastructure layer (OpenTofu) worked cleanly: old droplet destroyed,
new one created, reserved IP (`104.248.101.239`) and firewall reattached
without incident.

**The first automated pass failed at the Ansible bootstrap step**
("connection refused" on port 22) — the freshly created droplet's SSH
daemon wasn't ready yet when Ansible tried to connect, a transient timing
race in the recreate -> deploy handoff that pre-dates this spec (no
wait-for-ssh retry exists between droplet creation and the first Ansible
connection). Not caused by the tools/ reorg. Recovered manually: confirmed
SSH became reachable within seconds, re-ran `tools/ops/deploy.sh`, which
bootstrapped `dave` and completed the full site play (`ok=37, changed=30`).
`tools/ops/acceptance-test.sh` then passed all 5 checks against
`sask.davidstitt.net`, and a second consecutive `tools/ops/deploy.sh`
reported `changed=0`, confirming idempotency from the new tool location.

Reserved IP, DNS, and firewall survived unchanged throughout, per
REQ-OPS-013's guarantee. The SSH-readiness race is flagged in SPEC-029's
`[addendum]` as a real, pre-existing harness gap — adding a retry would be
a behavior change, out of this spec's path-reference-only scope, left for
a future spec.

**SPEC-029 flipped from `proposed` to `accepted`.**

## 2026-06-25 — SPEC-029: tools/ reorg into ops/dev/studio/helpers

**All 25 tools/ files moved** (`git mv`, history preserved) into four
buckets by kind: `tools/ops/` (13 — deploy/destroy/provision/
recreate-droplet/redeploy, connect, acceptance-test,
export-requirements, the three perf_* + perf-remote + run_perf),
`tools/dev/` (5 — pre-commit-check, run-tests, start_web,
validate_specs, generate_orbital_conditions), `tools/studio/` (2 —
build_assets, graphic_tweaks), `tools/helpers/` (5 — match_semver,
host_info, make_tree, validate_json, stamps). `tools/candidates/`
dissolved entirely.

**Found a class of bug the spec text never mentioned**, by reading the
actual scripts rather than trusting the spec's own suggested grep
patterns: every moved file sits one directory level deeper, and 11 shell
scripts (`cd "$(dirname "$0")/.."`) plus 3 Python tools
(`Path(__file__).parent.parent`) compute repo-root via depth-relative
math that assumed the *old* depth. Fixed all 14. The two tools already
one level deep in `tools/candidates/` (build_assets.py's `parents[2]`,
make_tree.sh's `../..`) needed no change — their new homes are the same
depth.

**Other real breaks fixed**: `pre-commit-check.sh`'s
`shellcheck tools/*.sh` glob would have matched zero files post-move
(verified empirically: 15/15 .sh files now caught by `tools/*/*.sh`);
`pyproject.toml`'s `pythonpath` updated from `["src", "tools"]` to
`["src", "tools/ops", "tools/dev"]` to keep the two bare tool imports
resolving (`perf_config` in tests/perf/, `generate_orbital_conditions` in
the default-collected test_spec_006.py); `test_validate_specs.py`'s
manual `sys.path.insert` updated to match. Every inter-tool call
(redeploy.sh -> recreate-droplet/deploy/acceptance-test; deploy.sh ->
export-requirements; perf-remote.sh -> acceptance-test + perf_engine/
perf_config/perf_http) and every tool's own self-referencing usage
comment fixed, plus the prose comments in infra/tofu/*.tf,
secrets/infra.env.example, ansible/bootstrap.yml, CLAUDE.md, README.md,
docs/deploy-runbook.md, docs/user_testing.md, docs/references.md, and
.gitignore that named a tool's old path.

No behavior change. Full unit suite still 626 passed; full perf benchmark
suite (20 benchmarks, now running from tools/ops/) still green — the real
regression check for the perf-tooling depth/pythonpath fixes. Pre-commit
suite clean from its new tools/dev/ home. App boots locally via
tools/dev/start_web.sh and serves real content.

**Next:** the live redeploy (`tools/ops/redeploy.sh -y`) is this spec's
remaining acceptance criterion — held back pending explicit confirmation
before touching the production droplet.

## 2026-06-25 — DD-0017/SPEC-028 B3: adapter homes; accepted

**`src/sask/api/` and `src/sask/cli/`** created, each with only an empty
`__init__.py` — placeholder homes for the next phase's adapters, no
adapter code. **`src/sask/templates/` moved into `src/sask/web/templates/`**
(`git mv`), with `web/__init__.py`'s one-line `template_dir` lookup updated
to match (`.parent` instead of `.parent.parent`, since templates is now a
direct child of `web/` rather than a sibling). This wasn't in any phase's
original scope — DD-0017/SPEC-028's own target_structure diagram already
showed `templates/` nested under `web/`, but no phase had actually moved
it; caught during the design-doc review and folded into B3.

Verified empirically that packaging discovery needs no pyproject.toml
change (`packages = [{include = "sask", from = "src"}]` already
auto-discovers subpackages) by importing every new package path
directly, and confirmed the app boots and serves locally with the moved
templates: `/`, `/moons`, `/ephemeris` all returned 200 with real content.

Full unit suite still 626 passed; full perf benchmark suite (20
benchmarks) still green at every phase (B1, B2, B3) — not just the
default suite, which would have missed the `tools/perf_engine.py`
regression risk found in B2. Pre-commit suite clean throughout.

**DD-0017 and SPEC-028 flipped from `proposed` to `accepted`.** SPEC-028
got an `[addendum]` documenting every gap found beyond its literal text
during implementation (own-module spine imports, absolute import-style
normalization, the perf-tooling and docs fixes, the ephemeris/lore
purity-test gap, the templates move) so the accepted record matches what
was actually built, not just what was originally proposed.

## 2026-06-25 — DD-0017/SPEC-028 B2: calendar bulk move

**The ten calendar modules** (`pulse`, `season`, `bodies`, `sky`, `scene`,
`lunar`, `stars`, `apparitions`, `ephemeris`, `lore`) **moved into
`src/sask/calendar/`** (`git mv`, history preserved), empty
`calendar/__init__.py`, no re-exports. Every module's own imports
normalized to absolute form: siblings as `sask.calendar.<mod>`, spine as
`sask.message`/`sask.config_loader` (`bodies.py`/`sky.py` already used
absolute spine imports and needed no change there).

**Fixed every consumer import site**, found by direct repo-wide grep
rather than trusting the spec's literal "src/ and tests/" pattern alone:
`src/sask/web/routes.py` (8 lines), 15 `tests/test_spec_*.py` files, and —
the one real gap beyond the spec's stated scope — `tools/perf_engine.py`
and `tests/perf/test_engine_benchmarks.py` (7 lines each), which live
outside `src/`/`tests/`'s literal grep pattern and outside the default
pytest run (`tests/perf` is in `norecursedirs`), so they'd have broken
silently. Also fixed a live, actionable example in
`docs/user_testing.md`'s REPL walkthrough (`sask.pulse`/`sask.season`
imports) that would otherwise have stopped working for the next person
who followed it.

**Relocated every hardcoded test-file path reference** to the ten moved
modules — broader than "layer-purity": includes the calendar-independence
and no-civil-arithmetic content checks on `apparitions.py`, `stars.py`,
`scene.py` that hardcode the same literal source path for a different
purpose. `ephemeris.py` and `lore.py` have no such test anywhere in the
suite — a pre-existing gap, not something this phase introduces; noted
rather than papered over with a new test (same test count throughout).

No behavior change. Full unit suite still 626 passed; full perf benchmark
suite (20 benchmarks, now importing through `sask.calendar.*`) still
green — the real regression check for the `perf_engine.py` rewrite, since
the default suite wouldn't have caught it. Pre-commit suite clean.

## 2026-06-25 — DD-0017/SPEC-028 B1: asset canary move

**`src/sask/asset.py` -> `src/sask/asset/retrieval.py`** (`git mv`, history
preserved), with an empty `asset/__init__.py` and no re-exports — the first
of the three reorg phases, smallest blast radius by design. Two real import
sites fixed: `src/sask/web/routes.py` and `tests/test_spec_026.py`, both now
`from sask.asset.retrieval import ...`. The one layer-purity check
(`test_asset_module_has_no_flask_import`) relocated to target
`src/sask/asset/retrieval.py`; still genuinely fails if the module imported
flask. No behavior change, no test-count change: full suite still 626.

## 2026-06-25 — Housekeeping: doc sweep, DD-0017/SPEC-028 added

**Post-rename reference sweep.** Repo renamed `sask-calendar` -> `sask`
(Phase A; GitHub remote renamed too). Swept every non-code doc and design
TOML for the stale name: `README.md`, `docs/glossary.md`,
`docs/user_testing.md`, `docs/vm-setup.md`, and 5 design TOMLs (DD-0002,
DD-0014, DD-0016, REQ-FUN-013, SPEC-023). The passages in DD-0014 and
DD-0016 that documented the *deliberate* sask/sask-calendar name mismatch
(and the "future repo-rename round") were reworded to state the rename is
complete (2026-06-25) rather than blind-swapped into nonsensical prose.
`docs/devlog.md`, `tests/results/*.md`, and the perf-benchmark JSON were
left untouched — literal historical captures, out of scope.

**DD-0017 + SPEC-028 added (status: proposed).** The functional-area/
adapter subpackage reorg that DD-0016 deferred to "the repo-rename round" —
`calendar/` and `asset/` subpackages, `web/`/`api/`/`cli/` adapter homes —
now has its decision and spec on file, ready to implement.

**`analysis/deployment/` and `analysis/functionality/` removed** —
superseded by the accepted DD-0014/DD-0016 design docs; archived on
Dropbox alongside the old `sask-proto` code, not deleted outright.

**Found and fixed a real bug along the way:** the local `.venv` predated
the rename — every shim in `.venv/bin/` (pytest, pymarkdown, ...) had a
hardcoded shebang pointing at the now-nonexistent
`/home/dave/Code/sask-calendar/.venv/bin/python3`. Regenerated per
`docs/vm-setup.md`'s documented procedure.

**Clean baseline verified before starting the reorg:** full pre-commit
suite (ruff, shellcheck, pymarkdown, validate_specs) green; full unit
suite 626 passed; a full `tools/redeploy.sh -y` destroy/recreate/deploy/
verify cycle run end-to-end against the live droplet — Ansible `37 ok, 31
changed, 0 failed`, acceptance suite all PASS against
`sask.davidstitt.net`.

**Next:** implement DD-0017/SPEC-028 in three phases (B1 canary asset
move, B2 bulk calendar move, B3 adapter homes).

## 2026-06-24 — SPEC-027 accepted: redeployed and verified live

**REQ-OPS-017/SPEC-027 redeployed against the real droplet and accepted.**
`bash tools/deploy.sh` shipped the new Ansible sync task and Caddy
rate-limit zone: `failed=0`, both new tasks fired (`Ensure the assets/
parent directory exists`, `Sync the versioned assets/ data tree`), both
`runtime`/`caddy` restart handlers fired, no crash on restart — confirming
the catalog config and its payload files land together, the exact failure
mode this spec exists to prevent. A second consecutive deploy reported
`changed=0`. Checked directly on the droplet: exactly the 7 real catalog
files under `/opt/sask/assets/v0/`, `assets/local/` correctly absent, and
the rendered Caddyfile carries the new `zone asset` block (20 events/1m)
exactly as designed. Layer 2 (`tools/acceptance-test.sh`) and Layer 3
(`tests/acceptance/`, including a new sha256 byte-identity check) both
green against `sask.davidstitt.net`.

**Delete-semantics verified with a disposable probe asset**, not a real
catalog entry — added a throwaway file + catalog entry, deployed,
confirmed live; removed both, deployed again, confirmed gone (404); final
no-op deploy reconverged at `changed=0`. Avoided ever letting the live
catalog reference a missing file mid-test, which would have crashed every
gunicorn worker on restart.

**Found and fixed a small real bug while running the suite for real:**
`tools/acceptance-test.sh`'s new asset checks captured the binary response
body into a shell variable just to discard it, producing a harmless but
noisy "ignored null byte in input" warning on every run. Fixed to write
the body to a temp file and read only the status code.

**The one `[manual]` item — rate-limit trip — confirmed by Dave directly:**
multiple rapid refreshes of `/asset/image/splash.bg` produced a 429,
confirming the zone is actually enforced, not just present in the
rendered config. Full results in `tests/results/SPEC-027.md`.

**Next:** nothing queued. The asset-retrieval effort (DD-0016 through
SPEC-027) is fully closed out — design, implementation, UAT, deploy, and
acceptance all done.

## 2026-06-24 — SPEC-026 accepted; SPEC-027 awaits redeploy

**DD-0016/REQ-FUN-013/SPEC-026 implemented, UAT passed, and accepted.**
Ported an improved version of the sibling `sask` project's small resource
server into a consumer-neutral, Flask-free asset-retrieval capability:
`src/sask/asset.py` (`resolve_descriptor`/`fetch_payload`/
`AssetNotFoundError`), two new frozen message units
(`AssetDescriptor`/`AssetPayload` in `message.py`), a load-once,
exhaustively-validated catalog joined to `AppConfig`
(`config/asset_catalog_data.toml`, loaded by `config_loader.py`'s new
`_load_asset_catalog`), and a thin HTML adapter route,
`GET /asset/<kind>/<id>`, in `routes.py`. `tests/test_spec_026.py` adds 18
tests (catalog validation, descriptor/payload round-trip, the no-file-read
guarantee on `resolve_descriptor`, layer-purity, the HTML adapter) — full
suite now 626 (was 608), zero regressions. Manual browser UAT (8 cases,
`docs/user_testing.md`) passed 2026-06-24: all seven real catalog entries
(four splash-image variants, one audio loop, one JSON asset, one video)
serve correctly with the right `Content-Type`, both 404 paths (unknown id,
unknown kind) behave identically, and no nav entry was added (consistent
with `/health`/`/ephemeris/download` precedent).

**A real design refinement surfaced during implementation, not anticipated
by the original draft of DD-0016/SPEC-026: "kind" is no longer an authored
catalog field.** It's derived from each asset's top-level subdirectory
under `ASSETS_DIR` (`image/`, `audio/`, `json/`, `video/`) — Dave's call,
made directly: "kind" serves little purpose as a fourth authored field
when the directory structure already partitions assets the same way, and
authoring it separately only created a way for an entry to disagree with
where it actually lives. `content_type` independence from file extension —
the property that actually matters for serving correct bytes — is
unaffected; only kind/directory independence was given up, and that's
recorded as a deliberate, revisitable tradeoff in DD-0016's
`kind_is_config`/`negative_or_deferred` sections, not a quiet drop.

**`load_config()` gained an optional `assets_dir` rather than a required
one** — the key implementation decision that kept this from being a
breaking change. `assets_dir` defaults to `config_dir.parent / "assets" /
"v0"` when omitted, so all ~20 existing `load_config(REAL_CONFIG)` call
sites (every other spec's test file, both perf tools, `wsgi.py`) needed
zero changes. `AssetCatalogEntry.path` stores the resolved *absolute* path
(computed once at load time), not the raw TOML string, which is what lets
`fetch_payload(descriptor, config)` keep its two-argument signature
without re-threading `assets_dir` through the engine layer.

**REQ-OPS-017/SPEC-027 (deployed asset sync + rate limiting) drafted and
implemented, but deliberately left "proposed" — not yet redeployed or
accepted.** A concrete gap analysis (reading the actual Ansible roles, not
assuming) found that `ansible/roles/app/tasks/main.yml` synced only
`src/sask/` and `config/`; since SPEC-026's catalog loader stats every
payload file at `create_app()` time, shipping the catalog config without
its files would raise `ConfigError` and crash every gunicorn worker, not
just asset routes — an availability risk, not a cosmetic gap. Added: a
versioned-assets sync task (mirroring the existing `config/` task, with
its own "ensure the parent directory exists" step — `assets/<version>/`
is two levels below `app_root`, the same rsync limitation `src/` hit
originally), a third Caddy `rate_limit` zone (`zone asset`, `/asset/*`,
20 events/1m — higher than the ephemeris-download zone's 4/1m since an
asset GET is one file read, not a computed scan, but still bounded for a
presently single-user service), and a live sha256 byte-identity
acceptance test mirroring sask-proto's own `test_image_bytes_match_local`.
`ansible-lint --profile production` is clean (fixed one real finding: a
task name with a mid-string Jinja template). Acceptance evidence
(`tests/results/SPEC-027.md`) is scaffolded with every check marked
PENDING — filling it in requires an actual redeploy, a deliberate,
human-triggered action not run as part of this pass.

**Side effects of this work, same session:** `shellcheck` added to
`flake.nix`'s devShell and `tools/pre-commit-check.sh` (`-S warning`,
excluding two deliberate info-level notes in `tools/perf-remote.sh`'s
client-side ssh-command variable expansion); fixed two real `cd`
robustness findings along the way. Separately, a full read-and-rewrite
pass over `tools/candidates/` (8 files inherited from the sibling `sask`
project, not wired into this app): deleted `assets_snip.py` (a broken,
superseded duplicate of `build_assets.py`), renamed `platform.py` ->
`host_info.py` (it shadowed the stdlib `platform` module, risky since
`tools/` is on `pythonpath`), and cleaned up env-var naming, docstrings,
and dead code across the rest. None of this is wired into the app; it was
explicitly a "make it clean before it's ever used" pass, not a feature.

**Next:** the manual redeploy + SPEC-027 evidence pass, whenever Dave
triggers it — not assumed or scheduled here.

## 2026-06-23 — SPEC-025: remote perf re-validation, ephemeris breach found

**DD-0015/REQ-OPS-016/SPEC-025 implemented and run for real against the
live droplet.** New `tools/perf_engine.py` (stdlib-only sibling of
`tests/perf/test_engine_benchmarks.py`) times the SPEC-018 hot paths and
ephemeris grid with plain `time.perf_counter()`, so it runs unmodified
against the production venv, which deliberately has no pytest-benchmark.
`tools/perf_http.py` gained `--skip-preview` and
`--download-warmup`/`--download-repeats`/`--download-delay-s` so the
remote HTTP sweep samples only the four interactive pages plus one spaced
request per ephemeris-download profile, staying well inside Caddy's
4-events/minute download limit. `infra/tofu/outputs.tf` gained
`droplet_size`/`droplet_region`/`droplet_vcpus` (applied: 0 resources
changed, output-only) so results carry a host stamp without a DO API
call. `tools/perf-remote.sh` orchestrates the whole procedure: acceptance
precondition, host identity, on-droplet engine timing over SSH (scp'd to
a tmp dir, run via `sudo` since `/opt/sask` is `sask:sask` mode 0750 and
`dave` has no group access, removed via a trap on exit regardless of
outcome), a comparable local engine run, the remote HTTP sweep, and a
merged `tests/results/perf/REMOTE-2026-06-23.json` + `.md`.

**Result: interactive budget confirmed; ephemeris budget breached, and
the breach is raw per-core compute, not redundant recompute.**

- Interactive pages: on-droplet `get_sky_scene` costs 0.70ms (0.26ms
  locally) - nowhere near the 500ms budget. Client wall-clock (117-181ms)
  is informational per DD-0015 and comfortable too.
- Ephemeris download worst case (30-day/5-min): end-to-end HTTP measured
  **16.60s (scribal)** and **12.03s (kinematic)** against the
  `[3.0, 5.0]`s budget - both fail by a wide margin.
- The on-droplet cross-check (no Caddy, network, or rate limit in the
  path) shows why: `get_sky_series` for the worst-case grid point alone
  costs 7.04s on the droplet vs 2.998s locally (2.35x); the worst-case
  renderers cost 2.03s/2.82s vs 0.75s/0.97s locally (2.71x/2.92x). Engine
  compute alone (series + render) already totals 9.07s (scribal) / 9.86s
  (kinematic) on the droplet - over budget before a single network byte
  moves. Every other hot path in the grid shows the same 2.3x-2.9x
  remote/local ratio, consistent with "this $6/mo single shared vCPU is
  genuinely slower per-core," not a deployment bug - SPEC-020/021 already
  removed the two real algorithmic redundancies (2026-06-21), and nothing
  new turned up here.
- The remaining gap between engine cost and end-to-end (7.53s scribal,
  2.17s kinematic) is transferring a 25.7MB / 16.5MB uncompressed JSON
  payload over the Madrid-fra1 link on a cold, single-sample, unwarmed
  request - DD-0015 deliberately takes one spaced sample per profile to
  respect the rate limit, so this isn't a median; real variance is
  expected here.

**DD-0015 rubric outcome: raw per-core compute.** Per DD-0015's explicit
guard, more vCPUs raise concurrency, not single-request latency, so a
same-tier resize is never the fix. The actual choice - a CPU-optimized
droplet tier, the regenerable cache anyway, or accept-and-document with
the export-time-estimate as UX mitigation - is recorded as its own future
decision, not implemented here; SPEC-025 is measurement-only by design
(its own out-of-scope line rules out implementing a cache or resizing in
this pass).

**Root cause of the per-core gap, confirmed empirically per Dave's direct
question** (is it the dev VM's 4 vCPUs? NixOS vs Ubuntu? something else?):
a trivial, stdlib-only, single-threaded Python loop with no app code at
all showed a **2.93x** gap between `sask-dev` (3.70s) and `sask-droplet`
(10.86s) - matching the 2.3x-2.9x engine-level gap almost exactly. That
rules out the obvious candidates: not the 4 vCPUs (the workload and the
probe are both single-threaded; `vmstat` on the droplet showed 0% steal
time during the test, so it isn't even active contention right now), and
not NixOS vs Ubuntu (same kernel family, same glibc, same CPython
generation - 3.12.13 vs 3.12.3 is a patch difference only, no JIT either
side). `sask-dev` is a KVM VM with access to Dave's real 11th-Gen Intel
i7-1165G7; `sask-droplet` is DigitalOcean's `s-1vcpu-1gb` *shared*-vCPU
Basic tier, whose model DigitalOcean reports only as the generic
`DO-Regular` (unlike the `c-` CPU-Optimized dedicated line) - a throttled
fractional core, intentionally slower per-core by the design of the
$6/mo tier. Not a deployment bug, not an algorithmic regression -
genuinely the hardware being paid for. Dave's read: "kind of like
deploying to an old Raspberry Pi found at the bottom of the closet."

**Next:** resolved the same day. Dave reviewed the results and chose
accept-and-document over a CPU-Optimized resize ($42/mo minimum, and only
the 2nd vCPU that DD-0015's own guard says wouldn't help anyway) or a
regenerable cache (real engineering work for a query space broader than
the one worst-case grid), and declined another design-doc round for it.
Committed and pushed as `f846f81`. DD-0015/REQ-OPS-016/SPEC-025 left as
"proposed" pending the still-unscoped, not-yet-requested
export-time-estimate feature and REQ-OPS-010 budget-text revision.

## 2026-06-22 — Runbook added; reboot-recovery confirmed for real

Added `docs/deploy-runbook.md` — quick-reference commands (connect,
status, deploy, full rebuild, full teardown), the OS-maintenance
procedure discussed below, and the operational facts worth remembering
(`dave` not root, `destroy.sh` vs `recreate-droplet.sh`, token expiry,
Caddy's auto-TLS, the DO console fallback).

Decided against automating OS patching as part of the redeploy pipeline:
`unattended-upgrades` already handles security patches continuously and
on its own schedule, independent of app-deploy frequency - coupling the
two would mean a routine code redeploy could also unexpectedly pull in a
kernel bump or an sshd restart. A kernel update specifically needs a
reboot to take effect, which would require the playbook to handle a
"check /var/run/reboot-required, reboot, wait for reachable" sequence -
real complexity for a benefit unattended-upgrades mostly already
provides. The existing gated `apt_upgrade` flag (default `false`) stays
the right mechanism for an occasional, deliberate full upgrade.

Dave ran the documented maintenance procedure for real: `apt upgrade`
(the ~150-package backlog from the base image) followed by a full host
reboot. **This also confirms, for real, the one REQ-OPS-015 acceptance
item that had only ever been "should work" rather than verified** - both
`sask.service` and `caddy.service` came back automatically after reboot
(systemd `enabled: true` on both) with no manual intervention, and
`https://sask.davidstitt.net/health` answered 200 within a couple of
minutes of the reboot. No issues found.

## 2026-06-22 — SPEC-024: acceptance suite, and a real destroy/redeploy gap closed

**SPEC-024 implemented and verified live.** Added `tools/acceptance-test.sh`
(Layer 2: curl-based, asserts TLS validity, `/health` 200, the rendered
root page contains the real story_now pulse value) and
`tests/acceptance/conftest.py`/`test_remote.py` (Layer 3: pytest with
`requests` against the real domain, no token fixture - public app). Both
ran clean against the live droplet. `tests/acceptance/` is excluded from
the default `pytest`/`pytest tests/` collection via `norecursedirs`
(confirmed: still 608, not 611). Added a new Poetry `acceptance` group for
`requests` - anticipated by the original design's "filter dev/acceptance
groups" language but never actually created - and confirmed
`export-requirements.sh` correctly excludes it from `requirements.txt`
(the droplet has no need for a testing-only HTTP client).

**Layer 4's full destroy -> reprovision -> redeploy cycle found a real
design gap, not a glitch.** Ran `tools/redeploy.sh -y` for real (with the
developer's explicit go-ahead, given the live site would be briefly
unreachable). It completed with `failed=0` - all three of SPEC-023's bugs
stayed fixed - but the **reserved IP itself changed**
(`129.212.194.54` -> `104.248.101.239`), contradicting REQ-OPS-013's
explicit guarantee that DNS and the SSH alias survive "with the reserved
IP held." Root cause: `destroy.sh`'s second `tofu destroy` call has no
`-target`, so it tears down every resource in state, including the
reserved IP itself - correct behavior for a genuine full teardown (which
is what `destroy.sh` is *for*, run standalone), but wrong for a redeploy
meant to preserve network identity. The site kept working throughout
(DNS updated correctly to the new IP) - this broke a guarantee, not
uptime.

Presented to the developer as a real design choice rather than silently
patched: keep `destroy.sh` as a full teardown, and add a narrower
`tools/recreate-droplet.sh` that destroys/recreates *only* the droplet
resource (reserved IP, DNS record, firewall, and SSH key registration all
stay untouched in Tofu state - Tofu's dependency graph handles
reassigning the IP and updating the firewall's `droplet_ids`
automatically). `tools/redeploy.sh` now calls `recreate-droplet.sh`
instead of `destroy.sh` + `provision.sh`, and also gained the verify step
(`acceptance-test.sh`) that didn't exist when SPEC-023 first wrote it -
the single `redeploy.sh -y` invocation now genuinely performs recreate ->
deploy -> verify as one act.

Re-ran the corrected cycle for real: `droplet_id` changed
(`579514354` -> `579520422`); **`reserved_ip` did not**
(`104.248.101.239` both before and after). `failed=0`, the verify step
passed automatically, DNS resolution and a follow-up idempotency check
(`changed=0`) both confirmed clean on the fresh droplet.

`design/specs/spec-022-tofu.toml` and `spec-023-ansible.toml` updated to
document `recreate-droplet.sh`. Evidence in `tests/results/SPEC-024.md`.

**This closes the deploy lifecycle work started with DD-0014.** SPEC-022,
023, and 024 are all implemented and verified live, not just designed.
Next: consider flipping DD-0014/SPEC-022/023/024 from "proposed" to
"accepted" now that all acceptance criteria are met.

## 2026-06-22 — SPEC-023: Ansible deploy live, three real bugs found and fixed

**SPEC-023 implemented and deployed for real** against `sask-droplet`:
`ansible/` (ansible.cfg, inventory.yml, group_vars/all.yml, site.yml, and
`base`/`runtime`/`caddy`/`app` roles) plus `tools/deploy.sh`, `connect.sh`,
`export-requirements.sh`, `redeploy.sh`. Also added: a minimal `/health`
route (`src/sask/web/routes.py`, no engine/config dependency by design),
`secrets/sask.toml.example` (the stubbed-but-unused app-secrets template),
and `go` to `flake.nix` (xcaddy needs it on PATH to build Caddy plugins,
not previously identified).

**`ansible/bootstrap.yml` added, not in the original spec draft.**
REQ-SEC-003's `PermitRootLogin no` leaves nothing able to log in once
applied, since the `sask` service user has no shell — discovered during
drafting, before anything touched the droplet. `bootstrap.yml` connects as
root (the only account on a fresh, no-cloud-init image) to create `dave`,
authorize the deploy key, and grant passwordless sudo; `tools/deploy.sh`
only invokes it when `dave` isn't already reachable. `design/specs/spec-023-ansible.toml`
updated to document this addition.

**Local validation before touching the droplet:** `ansible-lint` passed at
the "production" profile (after removing a `pip state=latest` task it
correctly flagged as a false-"changed"-every-run idempotency bug),
`--syntax-check` on both playbooks, and — rather than guessing at the
`mholt/caddy-ratelimit` plugin's Caddyfile syntax — actually built the
custom Caddy binary via `xcaddy` and ran `caddy validate` against the
fully-rendered config. All clean.

**Three real bugs surfaced only by running for real, all fixed and
re-verified:**

1. `bootstrap.yml`'s `remote_user: root` was silently outranked by
   `group_vars/all.yml`'s `ansible_user: dave` (a known Ansible precedence
   quirk) — it tried connecting as `dave` before that account existed.
   Fixed with an explicit `vars: ansible_user: root` in the play.
2. `rsync` can't create two missing destination directory levels in one
   pass — `base` only creates `app_root` itself, so the first sync to
   `app_root/src/sask/` failed (`app_root/src/` didn't exist). Fixed with
   an explicit directory-creation task first.
3. The first run's rsync failure aborted the play *before* the
   end-of-play handler flush, stranding two already-queued handlers: sshd's
   restart (so `PermitRootLogin no` was on disk but not yet active - root
   login still worked) and Caddy's restart (`enabled` but never actually
   `started` - zero journal entries). Fixed with `meta: flush_handlers`
   right after the sshd-hardening task, and `state: started` added to both
   the `sask` and `caddy` service-enable tasks. The live droplet's already-
   stuck state needed one manual `sudo systemctl restart ssh` to catch up
   (the file was already correct; only the running process wasn't).

None of these three were lint-detectable — all are runtime behaviors
(`ansible-lint` and `--syntax-check` stayed clean throughout).

**Full verification, all real, against the live droplet:**

- Idempotency: two consecutive `deploy.sh` runs, no manual steps between
  them, both `changed=0`.
- Security: `ssh -o User=root sask-droplet` now refused (publickey denied);
  `dave` works; `systemctl show sask` confirms `NoNewPrivileges`,
  `ProtectSystem=strict`, `ProtectHome`, `PrivateTmp` all active, not just
  present in the unit file.
- End-to-end HTTPS: `curl https://sask.davidstitt.net/health` -> 200 with
  every REQ-SEC-003 header present, valid TLS with no `-k`; `/` renders the
  real story_now pulse value (`104548096103`) - proof of the full DNS ->
  TLS -> Caddy -> gunicorn -> Flask -> engine -> template chain, not just a
  listening process.
- Rate limiting: 6 rapid requests to `/ephemeris/download` -> `400 400 400
  400 429 429`, exactly matching the configured 4-events/1-minute
  download-zone budget.
- Kill/restart: `pkill -9 -f gunicorn` -> systemd restarts within
  `RestartSec=5` (fresh PID, ~2s), `/health` answers 200 immediately after.

Evidence in `tests/results/SPEC-023.md`. The full destroy -> reprovision ->
redeploy cycle remains deferred to SPEC-024's Layer 4, same as SPEC-022.

**Next:** draft SPEC-024 (acceptance/operational test suite), then revisit
whether DD-0014/SPEC-022/SPEC-023 should flip from "proposed" to
"accepted" once that's done.

## 2026-06-22 — SPEC-022: droplet provisioned for real, sask_ed25519 passphrase removed

**`tofu apply` run for real** (`tools/provision.sh -y`) after a clean local
`tofu fmt`/`validate` and a read-only `tofu plan` review. All 7 resources
created in ~60s total: `digitalocean_ssh_key`, `digitalocean_droplet`
(`sask-droplet`, id `579490216`, `fra1`, `s-1vcpu-1gb`), `digitalocean_reserved_ip`
(`129.212.194.54`) + its assignment, `digitalocean_record`
(`sask.davidstitt.net` -> the reserved IP), `digitalocean_firewall`
(`sask-firewall`), and the generated `local_file` SSH config snippet. DNS
resolution and the DO console both confirm the A record. A second `tofu plan`
against the converged droplet reports "No changes" - the idempotency bar
holds.

**Found and fixed: `sask_ed25519` was passphrase-protected**, which silently
broke non-interactive SSH (the server accepted the public key, but the
client had no way to sign without the passphrase - classic "Server accepts
key" immediately followed by "Permission denied" in `ssh -vvv` output, with
no signing step in between). Root-caused via `ssh-keygen -y -f
~/.ssh/sask_ed25519 -P ''`, which fails cleanly with "incorrect passphrase"
without ever exposing key material. Decided with the developer to strip the
passphrase entirely (`ssh-keygen -p`, old passphrase entered once
interactively, new passphrase left blank) rather than set up a
session-persistent `ssh-agent` (the sibling project's approach) - this key
has no other use, and a passphrase-free deploy key is what makes
REQ-OPS-013's single-mainline `redeploy` actually unattended. Re-verified the
fix non-destructively (empty-passphrase decrypt now succeeds, still matches
the registered public key) before retrying; `ssh -o User=root sask-droplet`
now succeeds (Ubuntu 24.04.3 LTS confirmed).

**Unrelated cleanup, found during a DO API sanity check:** an old, unattached
firewall (`bow-spt-firewall`) from an unrelated, years-old project was
flagged and, on the developer's confirmation that it was unused, deleted
(`DELETE /v2/firewalls/{id}` -> HTTP 204). Only `sask-firewall` remains on
the account.

Evidence recorded in `tests/results/SPEC-022.md`. SPEC-022's
destroy/recreate-cycle acceptance check is deferred to SPEC-024's Layer 4,
where it's exercised together with SPEC-023's Ansible re-convergence rather
than bare Tofu alone.

**Next:** draft SPEC-023 (Ansible: base/runtime/caddy/app roles), starting
with the root-then-`dave` bootstrap sequencing already noted in
`infra/tofu/ssh-config.tf`.

## 2026-06-22 — DO deploy pre-flight: review and credentials check

**Design review.** Read `analysis/*`, `design/decisions/dd-0014-deploy.toml`,
`design/reqs/req-ops-013/014/015.toml`, `design/reqs/req-sec-003.toml`, and
`design/specs/spec-022/023/024.toml` for the upcoming DigitalOcean
deploy/destroy/redeploy work. All consistent; `validate_specs.py` passes.
Confirmed against the running repo: `flake.nix` is missing the new tooling
(`opentofu`, `ansible`, `ansible-lint`, `openssh`, `jq`, `curl`, `gh`,
`xcaddy`) the plan needs; `ansible/` and `infra/` (beyond
`configuration.nix`) are still empty placeholders; no `/health` route
exists yet in `routes.py`.

**DO account checked clean.** Confirmed via the DO console:
`sask.davidstitt.net` is not configured, and no droplet, DNS record, or SSH
key remains from the retired sibling `sask` project - all torn down
together. The parent zone `davidstitt.net` is DO-nameservered (3 NS
records, plus an unrelated existing apex A record). Billing is active;
droplet limit is 25, with 1 unrelated droplet active (a separate, still-live
host for a different project, found via an existing `~/.ssh/config` entry
and confirmed unrelated to this work).

**SSH key.** `~/.ssh/sask_ed25519`/`.pub` already exists on `sask-dev`
(modes 600/644, predates this session) - well-formed, ready for Tofu's
`digitalocean_ssh_key` resource to register with DO at `apply` time. No
manual DO-console step is needed for this.

**Credentials located, not regenerated.** `~/.config/sask/` on `sask-dev`
holds three files left over from the sibling project's own deploy work:
`infra.env`, `tokens.toml`, and `token_value`. Inspected structurally only -
key names and value *lengths*, never the secret values themselves, were
printed or logged. `infra.env` holds a single `DIGITALOCEAN_TOKEN` export
and is exactly the file `tools/provision.sh`/`destroy.sh` will source;
`tokens.toml` and `token_value` are the sibling project's own
*application*-level bearer-token secrets (unrelated to DO infrastructure)
and are not used by this deploy. `infra.env`'s token was confirmed live
with a read-only `GET /v2/account` call (HTTP 200, account/droplet-limit
details matched what was seen in the DO console) - no regeneration needed,
regardless of whether it is the same token as the `NIXSASK` Personal Access
Token (read/write scope, ~10 months remaining) visible under the account's
API settings.

**Decision: admin account name.** The droplet's SSH/operator login account
(distinct from the no-shell `sask` service user that REQ-SEC-003/SPEC-023
create) will be named `dave`, matching the host laptop and `sask-dev` VM
usernames. Bootstrap sequencing note for the implementation: a fresh,
no-cloud-init droplet only has `root` until Ansible creates `dave`, so the
first-ever Ansible connection must be as `root`, before sshd's
`PermitRootLogin no` hardening is applied.

**Next:** draft the SPEC-022 deliverables (`flake.nix` edit,
`infra/tofu/*.tf`, `tools/provision.sh`/`destroy.sh`,
`secrets/infra.env.example`) for review. No cloud action taken yet.

## 2026-06-21 — SPEC-021: kinematic ephemeris rendering fix

**SPEC-021 (DD-0013 / REQ-OPS-012) implemented.** `render_kinematic_json`
recomputed `all_body_states`/`all_sky_positions` from scratch for every
ephemeris step, even though `get_sky_series` already computed both (inside
`get_sky_scene`) for that exact pulse. `get_sky_scene` now takes optional
`body_states`/`sky_positions` keyword parameters (computed internally if
omitted - every existing caller, including the `/sky` route, is
unaffected). `get_sky_series` computes both once per step, passes them into
`get_sky_scene`, and stores them on the internal `_Step` record;
`render_kinematic_json` reads them from there instead of recomputing. 3 new
tests in `tests/test_spec_021.py`, including a byte-exact golden-snapshot
regression, confirm no behavior change. Full suite: 607 passed, no
regressions.

**Measured impact:** `render_kinematic_json`'s worst-case cost (8,640
steps) dropped from 2.37s to 0.98s (~2.4x). The end-to-end kinematic
ephemeris download, which had measured 5.25s (5% over REQ-OPS-010's 5.0s
upper bound), now measures **4.135s** - back within budget. The scribal
download remains within budget at 4.058s. **All six SPEC-018 budget checks
now pass** (four interactive pages + both ephemeris-download profiles).

`design/decisions/dd-0013-kinematic-body-positions.toml` and
`design/specs/spec-021-kinematic-body-positions.toml` status updated to
"accepted". Updated baseline JSON written to `tests/results/perf/`.

**Next:** present diff and results for review; commit on confirmation.

## 2026-06-21 — SPEC-020 fix + SPEC-018 performance baseline

**SPEC-020 (DD-0012 / REQ-OPS-011) implemented.** `get_cofullness`'s
per-night loop is now a private generator (`_cofullness_events` in
`src/sask/lunar.py`); `get_cofullness` is `list(...)` of it (unchanged
behavior), and a new `next_cofullness(start_pulse, config)` consumes the
same generator lazily, stopping at the first qualifying night instead of
scanning the full 5-year horizon and converting calendar dates for every
match along the way. `scene.py`'s `get_sky_scene` now calls
`next_cofullness` instead of taking the first item of `get_cofullness`'s
result. 5 new tests in
`tests/test_spec_020.py`, including golden-snapshot regressions captured
from the pre-refactor output, confirm no behavior change. Full suite: 604
passed, no regressions.

**Measured impact:** `get_sky_scene` dropped from ~27ms to ~258µs per call
(~105x). The worst-case `get_sky_series` (30-day/5-min, 8,640 steps), which
hadn't completed even one pytest-benchmark round in 30+ minutes before the
fix, now runs in 2.73s.

**SPEC-018 baseline recorded** (both layers, against the fixed engine):

- Layer 1 (`tests/perf/`, `tests/results/perf/benchmarks/`): all 20
  benchmarks complete in 59s total (previously didn't finish).
- Layer 2 (`tools/perf_http.py`, `tests/results/perf/2026-06-21_http.json`):
  all four interactive pages render in 0.7-1.2ms (budget 500ms, comfortably
  passed). Ephemeris download worst case: scribal 3.64s (within the 3-5s
  budget); **kinematic 5.25s (fails the 5.0s upper bound by ~5%)**.

**New finding, not yet addressed:** the kinematic worst case isn't a
cofullness problem — `render_kinematic_json` itself costs ~2.37s for the
8,640-step/~15-tracked-body worst case, comparable to `get_sky_series`'s own
2.73s. SPEC-020 only targeted the cofullness search; this is a separate,
now-dominant cost left for a future spec if/when prioritized.

`design/decisions/dd-0012-cofullness-next-event.toml`,
`design/specs/spec-020-cofullness-next-event.toml`, and
`design/specs/spec-018-performance.toml` status updated to "accepted".

**Next:** present diff and results for review; commit on confirmation.

## 2026-06-19 — SPEC-019: UAT complete (all 6 TCs pass)

**SPEC-019 UAT passed** (TC-019-01 through TC-019-06). During TC-019-04,
the browser rejected a valid Terpin long-turn day (37) before the request
reached the server: the `terpin_day` and `fatunik_month` HTML5 `min`/`max`
attributes on `/moons`, `/planets`, `/sky`, and `/ephemeris` predated
SPEC-019 and were too tight (`fatunik_month` capped at 12 instead of 13;
`terpin_day` capped at 30/35 instead of 37 — the Terpin long-turn festival
length). Normalised all eight fields to `month max="13"`,
`fatunik_day max="30"`, `terpin_day max="37"` across the four templates.
Full suite re-run after the fix: 599 passed; pre-commit clean.

**Next:** committed; performance testing (SPEC-018) is the next phase.

## 2026-06-19 — SPEC-019: festival-month validation — dev complete

Implemented REQ-FUN-012 / DD-0011: `fatunik_to_pulse` and `terpin_to_pulse`
(`src/sask/pulse.py`) now reject an out-of-range month or day with a typed
`CalendarRangeError(ValueError)` instead of silently rolling into the next
month. Added `fatunik_month_length`/`terpin_month_length` as the single
source of truth for a turn's per-month day count (extracted from the
converters' existing year-type logic — `_fatunik_festival_length` and
`_terpin_festival_length` — so converter and validator can never disagree).

No web-layer changes were needed: `_resolve_pulse`/`_resolve_endpoint`
(`src/sask/web/routes.py`) already catch `ValueError` from the converters and
render the existing in-page error, covering `/`, `/moons`, `/planets`,
`/sky`, and the `/ephemeris` start resolver for free.

20 new tests in `tests/test_spec_019.py` (festival boundaries across Fatunik
standard/leap and Terpin regular/long/super-long, regular-month overflow,
month-out-of-range, error-message content, pulse/Astro-day unaffected, and
web-layer rendering). Full suite: 599 passed, no regressions. Pre-commit
checks pass. `design/decisions/dd-0011-festival-months.toml` and
`design/specs/spec-019-festival-months.toml` status updated to "accepted".

**Next:** UAT — see `docs/user_testing.md` SPEC-019 section (TC-019-01..06).

## 2026-06-19 — Docs reconciliation: ephemeris range cap text

DD-0009 and SPEC-015 still described the ephemeris range cap as 7 days
(~2,016 steps), left over from before the SPEC-016 UAT change. Config
(`config/ephemeris_data.toml`) is and remains the source of truth at 30 days
(2,592,000 pulses); updated DD-0009 and SPEC-015 prose to 30 days (~8,640
records) to match. SPEC-016 already read 30 days; no change needed there.
No code or config touched.

## 2026-06-14 — SPEC-017: UAT complete (all 10 TCs pass)

**SPEC-017 UAT passed** (all 10 test cases — TC-017-01 through TC-017-10).

Lore overlay display confirmed correct in the browser for story_now pulse:
watch/shur/keyt for Fatunik and Terpin; era-based lore dates for fatunik_solar
and terpin_solar; phase-quarter dates for untamed, warren, and terpin_lunar;
ordinal day/turning for hearth. One minor refinement during UAT: hearth day and
turning count now rendered as ordinals (e.g., "1st", "51st").

**Next:** performance testing, packaging, Digital Ocean deployment.

## 2026-06-14 — SPEC-017: lore overlays — dev complete, awaiting UAT

Implemented lore overlay renderers (`src/sask/lore.py`) with 21 passing unit
tests. Pre-commit checks pass.

**Deliverables:**

- `config/lore_time.toml` — `enabled = true` added to `[display]`; unchanged otherwise.
- `src/sask/config_loader.py` — four new frozen dataclasses (`LoreAge`,
  `LoreCulture`, `LoreTimeConfig`, `CalendarLoreConfig`) plus `_load_lore_time()`
  and `_load_calendar_lore()` loaders; `AppConfig` updated with `lore_time` and
  `lore_calendars` fields; `load_config()` reads all six calendar TOML files.
- `src/sask/lore.py` — `render_lore_time(pulse, culture, config)`,
  `render_lore_date(technical_date, calendar_id, config)`, and
  `apply_lore_overlay(scribal_record, culture, calendar_id, config)`.
- `src/sask/web/routes.py` — sky() route computes Fatunik/Terpin lore times and
  solar/lunar lore dates when `cfg.lore_time.enabled`; passes all to template.
- `src/sask/templates/sky.html` — "Lore Overlay" section added (inside
  `{% if lore_enabled %}`), showing time and date for all 6 calendars.
- `tests/test_spec_017.py` — 21 tests covering config loading, `render_lore_time`
  (two cultures, boundary wrap, invalid culture), `render_lore_date` (all 6
  calendar types, festival month, age boundary), and `apply_lore_overlay`
  (presence, immutability, determinism).
- `design/specs/spec-017-calendar-rendering.toml` — status updated to "accepted".

**Next:** UAT — load `/sky` for story_now and verify the Lore Overlay section.

## 2026-06-14 — SPEC-016: UAT complete; form refactoring and validation additions

**SPEC-016 UAT passed** (all 16 test cases — TC-016-01 through TC-016-16).

Changes made during UAT that preceded commit (all tested and passing — 35 tests total):

**Form refactoring:**

- Input groups reorganised by type: Pulse fieldset (explicit start + end); Astro Day,
  Fatunik Date, Terpin Date fieldsets (start only; end computed from Duration).
- **Duration (Days)** replaces explicit end-date inputs for date modes (end = start + days × 86400).
- **Reset button** implemented as `<a href="/ephemeris">` (navigates to clean URL,
  clearing all fields); `<button type="reset">` was unusable because it restores to
  rendered values (which are the query-param values), not to empty.
- Computed end displayed inline to the right of the start time in each date fieldset
  (`End: [value] · HH:MM:SS`), rather than in a separate paragraph.
- All input types cross-populated after Generate regardless of which input type was used
  to specify the start (removed `and pulse_mode` guard from Pulse fieldset value attributes).

**Validation additions:**

- **Step ≥ duration** check: if `step_pulses >= (end_pulse - start_pulse)` the route
  returns a form error (200) and the download endpoint returns 400. The engine itself
  (SPEC-015) is unchanged — it correctly returns 1 step for this case; the web layer
  refuses it as a non-useful request. TC-016-16 covers this.
- **Range cap raised from 7 days to 30 days** (`range_cap_pulses`: 604800 → 2592000).
  Maximum request size is 8640 records at 5-minute intervals for 30 days. Error message
  in `ephemeris.py` updated accordingly. `test_range_at_cap_is_accepted` in
  test_spec_016.py now uses a 1-day step to keep CI fast (30 scenes vs 8640).
- Duration input `max` attribute updated to `30` in the template.

**Test counts:** 35 (test_spec_016.py); 64 combined with test_spec_015.py; 558 total.

---

## 2026-06-13 — SPEC-016: ephemeris web page and regen-on-download export

**SPEC-016 implemented** (26 new tests; 26 pass; UAT required before commit):

- `src/sask/web/routes.py` — two new routes:
  - `_resolve_endpoint(prefix, cfg)`: like `_resolve_pulse` but with prefixed query
    param names, allowing independent start/end endpoint resolution using all four
    input forms (pulse / Astro day / Fatunik date / Terpin date).
  - `GET /ephemeris`: form accepts start, end, step (minutes), and profile
    (scribal / kinematic / both). Generates a preview (first 5 steps) and passes
    scribal/kinematic JSON to the template as a `<pre>` block. Download links carry
    all parameters in the query string.
  - `GET /ephemeris/download`: reads start/end/step/profile from query string as raw
    pulses; validates throttle; regenerates JSON; returns as `attachment` with filename
    `ephemeris_{profile}_p{start}-{end}_s{step}.json`. No temp file written.
- `src/sask/templates/ephemeris.html` — server-rendered only (no JavaScript). GET
  form with all four input forms for start and end; step minutes; profile selector;
  truncated preview per profile in a scrollable `<pre>` box; download link(s).
- `src/sask/templates/base.html` — "Ephemeris" nav link added.
- `tests/test_spec_016.py` — 26 tests covering HTTP smoke, preview rendering,
  throttle validation, download headers, determinism, and JSON structure.
- SPEC-016 design doc status: `proposed` → `accepted`.

UAT: [manual] load `/ephemeris` in a browser; submit a valid range; inspect the
preview; click each download link; verify the file saves correctly.

---

## 2026-06-13 — SPEC-015: sky-scene ephemeris generator and JSON renderers

**Phase 0 — Design doc housekeeping (same session):**

- DD-0009, DD-0010, REQ-FUN-010/011, SPEC-015–017 authored and validated.
- `dd-0010-caelndar-rending.toml` renamed to `dd-0010-calendar-rendering.toml`.
- SPEC-017 deliverable paths corrected from `config/lore/` to `config/` (flat layout).
- Nine new config files committed: `ephemeris_data.toml` (required by SPEC-015);
  `lore_time.toml`, `calendar_lore_template.toml`, and six per-calendar lore overlay
  files (`fatunik_solar`, `terpin_solar`, `terpin_lunar`, `untamed`, `warren`, `hearth`)
  — authored, pending SPEC-017 implementation.

**SPEC-015 implemented** (29 tests, 523 total — no UAT gate; backend-only spec):

- `src/sask/config_loader.py` — `EphemerisConfig` dataclass (step floor, range cap,
  tracked bodies); `_load_ephemeris_data()`; `AppConfig` extended with `ephemeris`.
- `src/sask/ephemeris.py` — new module:
  - `get_sky_series(start, end, step, config)`: validates throttle (step ≥ 300 pulses /
    5 min; range ≤ 604,800 pulses / 7 days), iterates `get_sky_scene()` at each pulse,
    computes per-day context (season, body rise/transit/set) once per distinct Astro day.
    Returns `EphemerisSeries`. Pure and deterministic.
  - `render_scribal_json(series, config)`: readable per-step record — pulse, Astro day,
    time-of-day (HH:MM:SS), bodies above horizon, stars, active house, co-fullness,
    prose summary. No Fatunik, Terpin, or lore terms.
  - `render_kinematic_json(series, config)`: compact per-body alt/az, illumination, and
    above-horizon flag for all 15 tracked bodies including below-horizon positions (for
    smooth animation arcs).

---

## 2026-06-11 — SPEC-014: UAT complete (all 20 TCs pass)

UAT surfaced several corrections applied before sign-off:

- **Day-start times:** Removed the 2 AM deep-night snap. Fatunik date input
  now resolves to 06:00:00 (Fatunik day-start offset); Terpin and Astro day
  to 00:00:00. Time of day displayed inline next to the Astro Day query button
  on both `/sky` and `/moons`.
- **Layout:** Removed redundant "Date & Time" panel; Co-fullness moved
  immediately below Moons Above Horizon; Season moved above Fixed Stars.
- **Visibility consistency:** Bodies above horizon now require both
  `above_horizon` and `is_visible` (illumination threshold) everywhere —
  fixed in `scene.py` bodies_up filter and `translator.py` view models.
- **Brightness:** Changed observer-facing brightness from
  `albedo × illuminated_fraction × apparent_size` (always near zero, always
  "Dim") to `albedo × illuminated_fraction`. Re-calibrated labels:
  Brilliant ≥ 0.32, Bright ≥ 0.20, Moderate ≥ 0.10, Faint ≥ 0.04, Dim.
  Albedo column added to `/moons` table.
- **Near-full definition corrected:** Replaced time-based tolerance
  (`full_tolerance_days / T_syn`) with illumination-based threshold
  (`illuminated_fraction >= 0.90`). Slow moons like Endor (T_syn = 37 d)
  were excluded despite looking full to any observer; the new definition
  treats all moons the same way a medieval observer would. Config key renamed
  `full_tolerance_days` → `full_illumination_threshold`.
- **Co-fullness wording:** "Tonight" → "This day" throughout; window broadened
  from single midnight to full Astro day; `observable` flag added to
  `CofullnessTonightRef`; "(below the horizon throughout this day)" note shown
  when no near-full moon rises during the day.
- **Cosmetic:** Moon names capitalised in Lunar Calendars and Co-fullness
  sections; Terpin "mean" label left lower-case.

---

## 2026-06-10 — SPEC-014: unified sky-for-a-date web view

**SPEC-014 implemented** (31 tests, 494 total — unit tests complete; UAT pending):

- `src/sask/web/routes.py` — new `/sky` route: accepts pulse, Astro day,
  Fatunik date, or Terpin date; resolves to calendar day-start time; computes
  all date equivalents (Fatunik, Terpin, 4 lunar calendars), season, full sky
  scene, night summary, and image prompt.
- `src/sask/templates/sky.html` — single server-rendered page with panels for:
  Lunar Calendars (display-only), Moons above the horizon (linked to /moons),
  Co-fullness this day and next, Wanderers (linked to /planets), Comets &
  the Spark (when visible), Season, Fixed Stars & Houses, Night Summary,
  Image Prompt.
- `src/sask/templates/base.html` — Sky nav link added.
- No JavaScript; pulse rides in query string for bookmarking; date inputs
  cross-populate to show the resolved pulse.

---

## 2026-06-10 — SPEC-013: sky-scene composition and text rendering

**SPEC-013 implemented** (27 tests, 463 total):

- `config/sky_style_data.toml` — already authored; loaded into `AppConfig`
  via `SkyStyleConfig` and `SkyStyleSettings` dataclasses.
- `src/sask/config_loader.py` — `SkyStyleConfig`, `SkyStyleSettings`;
  `_load_sky_styles()` (validates default_style exists); `AppConfig` extended.
- `src/sask/message.py` — `BodyInScene`, `StarInScene`, `HouseRef`,
  `CofullnessTonightRef`, `NextCofullnessRef`, `SkyScene` message units.
  `validate()` improved to skip `X | None` fields (Optional sentinel pattern).
- `src/sask/scene.py` — new module: `get_sky_scene(pulse, config)` composes
  the full scene from all existing engine surfaces (SPEC-004/007/008/010/011/012);
  `render_night_summary(scene, config)` produces deterministic plain prose;
  `render_image_prompt(scene, config, style_id=None)` appends the selected
  style's medium/palette/composition/extra directives. No network call; no Flask.

---

## 2026-06-10 — SPEC-012: lunar calendars and co-fullness tracking

**SPEC-012 implemented** (60 tests, 436 total):

- `config/lunar_calendar_data.toml` / `config/cofullness_data.toml` — already
  authored; now loaded into `AppConfig` via new dataclasses.
- `src/sask/config_loader.py` — `LunarCalendarConfig`, `LunarCalendarSettings`,
  `CofullnessConfig` dataclasses; `_load_lunar_calendar_entry`,
  `_load_lunar_calendars` (expects exactly 4 `[[calendar]]` entries),
  `_load_cofullness`; `AppConfig` extended with `lunar_calendars`,
  `lunar_settings`, `cofullness`.
- `src/sask/message.py` — `LunarDate` and `CofullnessEvent` message units.
- `src/sask/lunar.py` — new module: `_synodic_period_days` (T_syn =
  1/(1/T_sid − 1/AstroYear); "mean" = arithmetic mean of all 8 moons);
  `_epoch_pulse` (fatunik or terpin anchor + offset); `get_lunar_date`
  (lunation, day, month, turn, short_count, long_count); `_round_turns_for`
  (smallest K turns realigning with AstroYear within tolerance, lru_cached);
  `near_full` (synodic phase within full_tolerance_days of opposition);
  `get_cofullness` (all midnight pulses in range with ≥ min_moons near-full).
  No Flask imports; no civil-calendar leap arithmetic.
- Four calendars: Untamed/Sella (12 months/turn, fatunik anchor);
  Warren/Shunna (21 months/turn); Hearth/Jembor (no-turns, lunation+day only);
  Terpin Lunar/mean (12 months/turn, terpin anchor).

---

## 2026-06-10 — SPEC-011: apparitions — recurring comets and the Spark

**SPEC-011 implemented** (43 tests, 376 total):

- `config/comet_data.toml` / `config/spark_data.toml` — already authored; now
  loaded into `AppConfig` via `CometConfig` and `SparkConfig` dataclasses.
- `src/sask/config_loader.py` — `CometConfig`, `SparkConfig` dataclasses;
  `_load_comets()` (expects exactly 3 `[[comet]]` entries), `_load_spark()`
  (singleton `[spark]` table); `AppConfig` extended with `comets` and `spark`.
- `src/sask/message.py` — `CometInfo`, `SparkInfo`, `ApparitionContext`
  message units.
- `src/sask/apparitions.py` — `get_apparitions(pulse, config)`: comet
  visibility from `perihelion_n = (n + epoch_offset) * period_pulses`, linear
  ramp to 0 at window edge; Spark via `_seeded_float(event_idx, salt)` — sha256
  hash over Kanka's 38-day rotation events, glimmer_probability 0.01,
  seeded exposure in [0.5, 3.0] days. No live RNG; fully reproducible.

---

## 2026-06-10 — SPEC-010: fixed stars and Houses of the Equinox

**Design work (all accepted):** DD-0005 (stars/houses), DD-0006 (apparitions),
DD-0007 (lunar calendars), DD-0008 (unified sky view); REQ-FUN-007/008/009;
SPEC-010–014. Config files added for all five upcoming specs.

**SPEC-010 implemented** (35 tests, 333 total):

- `config/star_data.toml` / `config/house_data.toml` — 16 fixed stars and 14
  Houses of the Equinox. Both files reformatted to valid TOML (original drafts
  used invalid semicolon-separated key-value pairs).
- `src/sask/config_loader.py` — `FixedStarConfig`, `HouseConfig`,
  `HouseNamingConfig` dataclasses; loaders; `AppConfig` extended.
- `src/sask/message.py` — `HouseInfo`, `FixedStarInfo`, `StarContext` message
  units.
- `src/sask/stars.py` — `get_star_context(pulse, config)`: active house from
  sidereal-arc placement (`HOUSE_ARC_OFFSET = 0.125`; season points fall
  mid-group: spring equinox → house 11, solstices/equinoxes → houses 2/5/8);
  visible stars = 4 perennial + 3 seasonal; 2 circumpolar houses always
  present. No civil-calendar config consulted.

---

## 2026-06-05 — SPEC-009 UAT: all tests pass; refactoring complete

**SPEC-009 UAT complete** — all 15 test cases pass (TC-009-01 through TC-009-13,
plus TC-009-07b and TC-009-11c added during the session). 298 tests total.

**Spec corrections surfaced by UAT:**

- *Endor eclipse (TC-009-03):* At pulse 0, Endor's synodic fraction (0.4778) is
  0.022 from opposition — within the 0.03 syzygy tolerance — and its ecliptic
  latitude is ≈ 0.27°, within the 0.8° node tolerance. Both conditions met →
  Lunar eclipse correctly fires. The original spec said "no eclipse"; the spec
  was wrong.
- *Zehembra illumination (TC-009-03):* `(1 − cos(2π × 0.823134)) / 2 ≈ 27.8%`,
  not 29.3% as the spec stated. The test doc contained a hand-calculation error.

**Bug fix — empty form fields (TC-009-06):**

All three fieldsets shared one `<form>`, so clicking any Query button submitted
all fields. Empty fields arrived as `""` (not absent), causing `float("")` to
raise ValueError and return an error instead of falling through to the intended
input type. Fixed with `or None` on every `request.args.get()` call in
`_resolve_pulse`.

**Input improvements:**

- Forms split into **four separate `<form>` elements** (one per fieldset); each
  Query button now submits only its own fields.
- **Terpin date input** added to `/moons` and `/planets` (priority chain: pulse
  \> astro\_day \> fatunik date \> terpin date).
- After any successful query, **all four input groups are cross-populated** with
  equivalent values (pulse, Astro day, Fatunik date, Terpin date) so the user
  can immediately re-query from any calendar system.
- Meta line above the results table simplified to show only Fatune horizon
  status; date equivalents are now visible in the populated input fields.

**Display improvements:**

- Removed duplicate illumination % from the Visible column (was shown in both
  Lit and Visible; kept only in Lit).
- Planets table restructured to a **two-row layout** per planet: main row
  (11 columns: name, colour, phase, lit, visible, altitude, azimuth,
  rise/transit/set, brightness) + light-grey detail row (spans full width:
  "Through a glass" | "Notes"). Eliminates the compressed Notes column of the
  previous 13-column single-row layout.
- "Through a glass" empty state now distinguishes: *"Appears as a plain disc;
  no notable features."* (visible, no rings/moons) vs *"Not currently
  visible."* (lost in glare). Previously showed a bare `—`.

**Design note — short-month date overflow (future consideration):**

Entering a day beyond the festival month's actual length (e.g., month=1, day=10
on a standard Fatunik year where the festival has only 5 days) silently overflows
into month 2. This is arithmetically consistent — both `fatunik_to_pulse` and
`terpin_to_pulse` use the correct festival-day count for the given year type
(standard / long / super-long). Marked for a future spec: add explicit validation
that rejects out-of-range festival-month day values with a user-visible error.

---

## 2026-06-04 — SPEC-006 through SPEC-009: orbital mechanics and sky UI

**SPEC-006** (26 tests) — Frozen orbital initial conditions committed to
`config/body_data.toml` for all 8 moons and 7 planets: epoch offset, sidereal
period, inclination, node, diameter, albedo, distance/semi-major axis.
Design docs DD-0004, REQ-FUN-010–014, SPEC-006–009 added.

**SPEC-007** (42 tests) — Body kinematics engine (`src/sask/bodies.py`):
sidereal/synodic fractions, ecliptic coordinates, illuminated fraction
(`(1−cosθ)/2` for moons; law-of-cosines phase angle for planets), visibility
scalar, eclipse detection (node-gated syzygy within configurable tolerances),
`BodyState` message unit, `all_body_states()`.

**SPEC-008** (26 tests) — Local-sky position engine (`src/sask/sky.py`):
ecliptic→equatorial→horizontal coordinate transform, rise/transit/set pulse
arithmetic, circumpolar/never-rising edge cases, Fatune sky position,
`SkyPosition` message unit, `all_sky_positions()`.

**SPEC-009** (48 tests) — Web UI for `/moons` and `/planets` pages:
`MoonViewModel`, `PlanetViewModel` and translators in `translator.py`;
routes in `routes.py`; Jinja templates (`moons.html`, `planets.html`);
eclipse row highlighting (solar = amber, lunar = blue); lore overlay
(apparent colour, ring description, visible moons, notes) layered at
the route, not in the engine.

**Calendar epoch corrections (same session):**

- Astro epoch: year 0, spring equinox, pulse 0 (midnight).
- Fatunik epoch: Astro year 1531, summer solstice, 6 AM → `epoch_astro_day = 559278`.
- Terpin epoch: Astro year 1043, spring equinox → `epoch_astro_day = 380948`.
- `story_now` locked to Astro year 3313, spring equinox; pulse = 104548096103
  → Fatunik T1782 M10 D29; Terpin T2271 M2 D2; season: Stillness / near Green Day.

252 tests total at end of this session.

---

## 2026-06-02 — SPEC-003 + SPEC-004: calendar conversions and seasonal context

**SPEC-003** (59 tests) — Astro↔Fatunik and Astro↔Terpin translators in
`src/sask/pulse.py`: `astro_to_fatunik`, `fatunik_to_pulse`,
`fatunik_turns_to_pulse_range`, `astro_to_terpin`, `terpin_to_pulse`,
`terpin_shell_of_turn`, `terpin_turn_within_shell`. Leap arithmetic for both
calendars (Fatunik long/super-long years; Terpin long years).

**SPEC-004** (25 tests) — Seasonal context (`src/sask/season.py`):
`SeasonInfo` message unit, `season_info()` — maps orbital position to one of
four seasons (Greening, Blazing, Harvest, Stillness) and detects proximity to
solstice/equinox events (Green Day, Blaze Day, Golden Day, Still Day).

UAT run as a Python REPL session on the VM; all TC-003-xx and TC-004-xx pass.
Results recorded in `tests/results/user_tests/`.

157 tests total (14 validate\_specs + 46 SPEC-002 + 13 SPEC-005 + 59 SPEC-003 + 25 SPEC-004).

---

## 2026-06-02 — SPEC-005: Flask UI thin vertical slice

**SPEC-005 implemented** — 12 tests, all pass (72 total):

- `src/sask/web/__init__.py` — `create_app()` factory; config loaded once, stored in
  `app.config`; template folder resolved relative to `__file__`
- `src/sask/web/routes.py` — `GET /?pulse=<n>`; float input rounded; errors rendered
  in-page
- `src/sask/web/translator.py` — `PulseViewModel` dataclass + `to_pulse_view()`; formats
  `day_pulse_offset` as `HH:MM:SS`, orbital position as `25.0000%`
- `src/sask/templates/base.html`, `index.html` — server-rendered Jinja, no JavaScript
- `wsgi.py` — gunicorn entry point at project root
- `pyproject.toml` — added `flask >= 3.0` and `gunicorn >= 22.0` runtime dependencies
- `tests/test_spec_005.py` — HTTP smoke, float rounding, error path, no-script, and
  AST layer-purity checks (engine files must not import flask)

Also in this session: `pulse_of_day` renamed to `day_pulse_offset` throughout
(`message.py`, `pulse.py`, `test_spec_002.py`).

**Next:** SPEC-003 (solar calendar conversions) + SPEC-004 (seasons).

## 2026-06-02 — SPEC-002: pulse/day core and config foundation

**Design documents added** (DD-0002, DD-0003, REQ-FUN-001–005, REQ-OPS-006–009,
SPEC-002–005, `docs/glossary.md`):

- DD-0002 — calendar engine architecture: pure functions over pulse + config, astronomy/civil
  separation, normalised [0,1) quantities, apparition model, message units
- DD-0003 — presentation architecture: Flask/Jinja in-process, message-unit seam, API-ready
- REQs and SPECs cover pulse core, solar calendars, seasons, and UI thin vertical slice

**SPEC-002 implemented** — 46 tests, all pass:

- `config/` — `time_constants.toml`, `calendars.toml` (astro, fatunik, terpin),
  `seasons.toml`, `timeline.toml`
- `src/sask/message.py` — frozen dataclasses: `PulseInfo`, `CalendarDate`, `SeasonInfo`
- `src/sask/config_loader.py` — typed config dataclasses, `load_config()`, `ConfigError`
- `src/sask/pulse.py` — `astro_day()`, `day_pulse_offset()`, `orbital_position()`,
  `civil_day()`, `pulse_info()`; translator stubs for SPEC-003
- `tests/test_spec_002.py` — signed pulse arithmetic, orbital position, day-start offset,
  config loading and validation
- `pyproject.toml` — added `pythonpath = ["src"]` for pytest

**Tooling:**

- `scripts/` removed; `tools/pre-commit-check.sh` and `tools/run-tests.sh` added
- `ruff` scope extended to `src/`; all 5 pre-commit checks pass
- 60 tests total: 14 validate_specs + 46 SPEC-002

Corrections applied during pre-commit: DD IDs fixed to 4-digit form; REQ schema
extended with `FUN` category; `rationale` added to all 9 new REQ docs; glossary
line lengths fixed.

**Next:** SPEC-005 (Flask UI thin vertical slice), then SPEC-003 + SPEC-004.

## 2026-06-01 — SPEC-001: VM steps complete, SPEC-001 fully PASS

Completed all manual VM steps from docs/vm-setup.md:

- `nixos-rebuild switch` applied; hostname confirmed `sask-dev`
- Key-only SSH verified (password auth rejected)
- `nix develop` confirmed: Python 3.12.13, Poetry 2.2.1, ruff 0.14.6
- `flake.lock`, `poetry.lock`, `requirements.txt` generated and committed

Fixes applied during VM steps:

- `flake.nix`: added `POETRY_VIRTUALENVS_PREFER_ACTIVE_PYTHON=true` and
  `LD_LIBRARY_PATH` fix — required for venv creation inside NixOS devShell
- `docs/vm-setup.md`: replaced `poetry export` with `poetry run pip freeze`
  (`poetry-plugin-export` not available in the pinned environment)
- `CLAUDE.md`: clarified ruff comes from nix devShell, not pip

SPEC-001 acceptance criteria all PASS.

## 2026-06-01 — SPEC-001: initial commit and VM configuration revised

Initial bootstrap commit pushed to `genuinemerit/sask-calendar` on GitHub.

VM approach updated: switched from provisioning a fresh headless NixOS VM to
reconfiguring an existing NixOS 25.11 KDE Plasma VM. Updated
`infra/configuration.nix` to a full replacement config (preserving KDE desktop,
adding key-only SSH hardening), pinned `flake.nix` to nixos-25.11, and rewrote
`docs/vm-setup.md`.

## 2026-05-31 — SPEC-001: repository scaffold

Stood up the sask repository from scratch on the Ubuntu host per DD-0001.

**Completed (Ubuntu host):**

- Full directory tree with `.gitkeep` in empty dirs
- Root files: `LICENSE`, `.gitignore`, `.editorconfig`, `pyproject.toml`, `flake.nix`
- Design schemas: `_schema.toml` for decisions, reqs, and specs
- Schema-enforcing `tools/validate_specs.py` and `tests/test_validate_specs.py`
- `infra/configuration.nix` — NixOS 25.11, user dave, key-only SSH, KDE desktop preserved
- Standard docs: `README.md`, `devlog.md`, `references.md`, `vm-setup.md`

**Deferred to VM (manual):**

- `nixos-rebuild switch` against `infra/configuration.nix`
- `flake.lock` and `poetry.lock` generation
- `requirements.txt` export

**Next:** DD-0002 — calendar engine representation (fixed-day core, 8 moons, wanderers).
