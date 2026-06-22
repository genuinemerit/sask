# analysis/

**Status (2026-06-22): superseded by design, and now by a real, live
deployment.** The questions this folder raised are answered in
[DD-0014](../design/decisions/dd-0014-deploy.toml),
[SPEC-022](../design/specs/spec-022-tofu.toml),
[SPEC-023](../design/specs/spec-023-ansible.toml), and
[SPEC-024](../design/specs/spec-024-acceptance.toml) — all four are now
`accepted`, implemented, and verified against the live droplet at
sask.davidstitt.net, not just designed. See `tests/results/SPEC-022.md`
through `SPEC-024.md` and `docs/devlog.md` for what was actually built and
the real bugs found running each piece for the first time;
`docs/deploy-runbook.md` for day-to-day operation. This folder remains as
supporting research and is not being rewritten to match every downstream
decision — treat anything below that conflicts with the DD/SPECs or the
evidence files as historical, not authoritative.

Research output, not design. This directory captures what was learned from
reviewing the sibling `sask` project's infrastructure-as-code and deployment
automation, with a view to porting that pattern into `sask-calendar`. Nothing
here is a DD, REQ, or SPEC — it is the homework that should precede drafting
those documents.

## Why this exists

`sask-calendar`'s own design docs already anticipate this work:

- [DD-0001](../design/decisions/dd-0001-scaffolding.toml) followups list
  "DD: hardened DO deploy/destroy/redeploy lifecycle" as deferred, not done.
- [DD-0003](../design/decisions/dd-0003-ux-and-service.toml) followups repeat
  the same item and note "the hardened deploy/destroy/redeploy lifecycle
  remains a separate DD."
- [SPEC-005](../design/specs/spec-005-ux-mvp.toml) scope item: "Deployable
  behind Caddy on the droplet, **reusing the sask deploy pattern**."
- [REQ-OPS-003](../design/reqs/req-ops-003.toml) lists `/scripts` in the
  agreed repo tree, but sask-calendar's actual, established convention is to
  put orchestration scripts under `/tools` (where `pre-commit-check.sh`,
  `start_web.sh`, and `run-tests.sh` already live) — corrected post-review,
  2026-06-21. `/scripts` is not being created; the new orchestration scripts
  land in `/tools` alongside the existing ones. REQ-OPS-003's text is stale on
  this point but not enforced by any validator, so it was left as-is rather
  than edited in this pass.

So the porting target is not a hypothetical — it's a named, accepted
follow-up with an explicit pointer at the source pattern to reuse.

## Scope

Source material is the `sask` project only (`~/Code/sask`), filtered to
**deployment automation**: provisioning, configuration management,
orchestration scripts, secrets handling, and the testing layered on top of
all of that. `sask`'s application code (a small authenticated resource
server — bearer-token auth, manifest-driven image/JSON/audio delivery) is
explicitly out of scope and excluded below, except where a detail of it
(e.g. Flask app-factory vs module-level `app` object) directly determines a
deployment artifact like a gunicorn `ExecStart` line.

No GitHub Actions or other CI-vendor automation is involved anywhere in the
source material — `sask`'s own ADR-0001/PR-001 deliberately rejected remote
CI ("Decided against GitHub Actions and remote CI; everything runs
locally"). Everything described here is bespoke OpenTofu + Ansible + bash,
run from the developer's machine. That matches what was asked for.

## Reading order

0. [deploy-port-plan.md](deploy-port-plan.md) — **start here.** The current,
   self-contained implementation plan: decisions made, sequencing, file-by-file
   deliverables per SPEC, and pre-flight checks. Written so a session opened
   only within `sask-calendar` (no access to the sibling `sask` repo) has
   everything it needs.
1. [source-inventory.md](source-inventory.md) — what was reviewed in `sask`,
   file by file, and what was deliberately excluded as functional.
2. [deployment-architecture.md](deployment-architecture.md) — the three-layer
   architecture (OpenTofu / Ansible / scripts), how idempotency was actually
   achieved, and the concrete pitfalls hit and fixed along the way.
3. [testing-strategy.md](testing-strategy.md) — the four-layer testing
   discipline `sask` applied to its deploy lifecycle, mapped onto
   `sask-calendar`'s existing `SPEC-NNN` / `tests/results/` conventions.
4. [porting-plan.md](porting-plan.md) — concrete file-by-file and
   naming-by-naming adaptation plan as originally drafted; superseded in
   detail by DD-0014/SPEC-022-024 and by `deploy-port-plan.md`, kept for the
   technical-adaptation facts it captured (gunicorn ExecStart, directories to
   sync) that are still accurate.
5. [open-questions.md](open-questions.md) — decisions only the user can make;
   all resolved — see DD-0014.

## What this is not

- Not a DD, REQ, or SPEC — none of the TOML schemas under `/design` are used
  here on purpose, since this is pre-design research, not a decision record.
- Not code. No `.tf`, `.yml`, or `.sh` files were created under
  `sask-calendar` in this session.
- Not a verdict on `sask`'s application architecture — that side of `sask`
  was read only enough to identify it as out of scope.
