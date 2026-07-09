# `tools/` Ops-vs-CLI Classification (SPEC-034)

Classifies every script currently under `tools/` against DD-0021's boundary
principle: does the capability act on the running **app/engine** (message
units, engine functions, the app's own log stream — CLI-nature, `src/sask/cli/`)
or on the **infrastructure** sask runs on (provision, deploy, droplet
lifecycle, host config — ops-nature, `tools/ops/`)? A refinement: capabilities
that **mutate** the running service stay in the ops harness even when they
touch the app, to preserve Ansible as the single source of truth.
**Recommend-only — no script is edited, moved, or migrated in this pass.**

## `tools/ops/` — infrastructure/deploy/service lifecycle (stays ops)

All of the following act on infrastructure (the droplet, DNS, firewall,
reserved IP, remote host state) rather than on the running app's own
data/log stream, or explicitly run local→remote — squarely ops per DD-0021:

| Script | What it does | Classification |
|---|---|---|
| `deploy.sh` | Deploys/re-converges sask onto an already-provisioned droplet via Ansible | Ops — infra convergence |
| `provision.sh` | Provisions/re-converges the droplet via OpenTofu | Ops — infra provisioning |
| `destroy.sh` | Tears down the droplet and every OpenTofu-created resource | Ops — destructive infra lifecycle |
| `recreate-droplet.sh` | Recreates only the droplet, preserving reserved IP/DNS/firewall/SSH-key state | Ops — infra lifecycle |
| `redeploy.sh` | The mainline recreate→deploy→verify act in one invocation (REQ-OPS-013) | Ops — infra lifecycle orchestration |
| `connect.sh` | SSHes to the droplet via its alias (REQ-OPS-014) | Ops — remote access, the sole IP reference point |
| `acceptance-test.sh` | Layer 2 (SPEC-024) curl smoke test against the live HTTPS endpoint | Ops-adjacent — deploy-time acceptance gate, runs remote |
| `export-requirements.sh` | Regenerates `requirements.txt` from `poetry.lock` | Ops/build — packaging step, not app-runtime-facing at all |
| `perf-remote.sh` | SPEC-025 remote performance re-validation, merges on-droplet + local timing | Ops — runs over SSH against the droplet |
| `run_perf.sh` | Runs the SPEC-018 Layer 1 engine benchmarks locally, saves a baseline | Ops/dev tooling — local benchmarking, not app-runtime-facing |
| `perf_config.py`, `perf_engine.py`, `perf_http.py` | Shared perf grid/budgets; stdlib-only engine timing (local or SSH); HTTP timing harness against a live gunicorn | Ops support modules for the perf scripts above — same classification |

None of these are candidates for CLI migration: they either act on
infrastructure directly, require remote execution the CLI is explicitly
forbidden from doing (DD-0021: "no remote-execution or credential logic"),
or are local build/benchmark tooling with no notion of "the app's own
running state" to query.

## `set-log-level.sh` — mutates the running service, stays ops

Runs `ansible-playbook site.yml --tags runtime -e sask_log_level=<LEVEL>` and
restarts the service — a genuine mutation of production configuration and
process state. DD-0021 names this script *by name* as the worked example of
why service-mutating capabilities stay ops-side even though they superficially
"act on the app": routing the change through Ansible, rather than a direct
SSH+sed edit, keeps Ansible the single source of truth so a later plain
`deploy.sh` doesn't silently revert a hand-edit.

**Correction to record, not a migration:** the script's own header comment
says it is "written as a standalone script... and later from the CLI's
log-level-change command (once the CLI exists)" — that aspiration is
**superseded by DD-0021's explicit written decision** that service mutation
stays ops-side. Recommend the comment be corrected to remove the "later from
the CLI" framing next time this file is touched for an unrelated reason; not
worth a dedicated edit in this analysis-only pass.

## `verify-logging.sh` — the one genuine straddler

Already read in full. Two distinguishable halves inside one script:

1. **App-output check** (the `REMOTE_CHECK` Python heredoc): SSHes to the
   droplet and inspects recent `journalctl -u sask` output for at least one
   well-formed structured JSON line and zero cleartext secrets. This is
   read-only and acts on the app's own log stream — CLI-shaped by DD-0021's
   principle, *in spirit*.
2. **Infra-config check**: confirms `/etc/systemd/journald.conf.d/sask.conf`
   exists on the droplet with the expected `SystemMaxUse`/`MaxRetentionSec`
   values, plus an informational `journalctl --disk-usage` read. This is a
   deploy-configuration concern, not an app concern — ops-shaped.

**Complication that prevents a clean 1:1 migration today:** as written, the
whole script only runs **remote** (via `tools/ops/connect.sh`, SSH to the
droplet) — there is no local/dev mode. DD-0021's dev/prod model says the CLI
"always acts on its OWN environment... no remote-execution... logic in the
CLI." A CLI command wrapping half 1 would need to run *against whichever
environment the CLI itself is running in* (dev's `sask-dev` journal locally,
or prod's `sask` journal when the CLI happens to be invoked on the droplet
via SSH) — structurally identical to how SPEC-034's own `logs query` command
already needs to work. It does not need SSH logic of its own; it needs to be
*invoked* on the droplet, the same way `logs query` will be.

**Recommendation (surfaced, not actioned this round):** half 1 (the app-JSON/
no-secrets check) is a good candidate for a **future** `logs verify`-style CLI
admin command, reusing `logs query`'s own `journalctl`-wrapping machinery
(SPEC-034) — once that machinery exists, it becomes straightforward to add.
Half 2 (drop-in config presence) should either stay in `tools/ops/` as-is or
move to an Ansible-level assertion (e.g. a post-deploy check task) — it has no
natural CLI home since the CLI has no infrastructure-config-inspection role.
This is a proposal for a **later** decision (a future SPEC), not something
this analysis resolves or schedules.

## `tools/dev/` and `tools/helpers/` — a third bucket, neither ops nor CLI

DD-0021's boundary is binary by design (app/engine vs. infrastructure), but
two existing `tools/` subdirectories don't fit either side, because they
don't act on the *running* sask app/engine at all:

- **`tools/dev/init-dev-host.sh`, `verify-clean-env.sh`, `verify-do-secrets.sh`**
  — one-time host bootstrap and environment verification. They run before
  there is a running app to query, and have no notion of "sask's own state."
- **`tools/dev/pre-commit-check.sh`, `run-tests.sh`, `validate_specs.py`,
  `generate_orbital_conditions.py`** — repo/dev tooling (linting, test
  running, design-doc validation, a one-off data-generation script), not
  app-runtime-facing.
- **`tools/dev/start_web.sh`, `tools/dev/sask-dev-service.sh`** (the latter
  new this round, SPEC-033) — dev-environment *process management* for the
  developer's own local app instance (start/stop/install the dev server).
  Adjacent to, but distinct from, both ops (no infrastructure/droplet
  involvement) and the future CLI (the CLI's commands *query* running-app
  state; they don't start or stop the process itself — process lifecycle
  stays a `tools/dev/` concern, matching how service *mutation* stays
  `tools/ops/` on the prod side).
- **`tools/helpers/{match_semver,stamps,host_info,validate_json}.py`,
  `make_tree.sh`** — small, generic, sask-app-unaware utility functions
  (confirmed by the first-pass port analysis to have no dependency on
  `sask`'s engine, config, or web layers at all). No boundary question
  applies to code that doesn't touch the running app in the first place.
- **`tools/studio/build_assets.py`, `graphic_tweaks.sh`** — asset-authoring
  tooling, run at content-preparation time, not against a running app
  instance.

**Recommendation:** name this explicitly as a third, out-of-scope-for-DD-0021
bucket rather than force a binary classification onto scripts the boundary
principle was never meant to cover.

## Summary

- **No migrations this round** (per SPEC-034's explicit scope-out).
- **One concrete follow-on proposal** for a later decision: a future `logs
  verify` CLI command absorbing `verify-logging.sh`'s app-output half, once
  `logs query`'s journalctl-wrapping machinery exists to build it on.
- **One stale-comment correction** to make whenever `set-log-level.sh` is
  next touched for an unrelated reason (not this pass): remove the "later
  from the CLI" aspiration, since DD-0021 has since settled that
  service-mutating capabilities stay ops-side.
- **Everything else in `tools/ops/`** stays ops, cleanly, with no ambiguity.
- **`tools/dev/` and `tools/helpers/`** are a third bucket outside DD-0021's
  scope entirely — no action, no ambiguity to resolve.
