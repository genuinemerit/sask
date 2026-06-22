# Source inventory — what was reviewed in `sask`

All paths below are relative to `~/Code/sask` unless noted. "In scope" means
it informed the porting plan; "Out of scope" means it was identified as
application-functional (resource-staging/-serving) and set aside per
instructions.

## Decisions (ADRs) — `decisions/`

| File | Title | Scope |
|---|---|---|
| `0001-secrets-policy.toml` | Secrets handling policy | **In** — two-category secrets split is the basis of `secrets/` handling in the port. |
| `0003-tofu-state-management.toml` | OpenTofu state management | **In** — local-state decision and its documented migration path. |
| `0004-deployment-topology.toml` | Single droplet, reserved IP | **In** — droplet/network/firewall/DNS shape. |
| `0005-service-deployment.toml` | Ansible + gunicorn + Caddy | **In** — the configuration-management layer. |
| `0006-application-secrets-deployment.toml` | App token deployment via Ansible | **Partly in** — the *mechanism* (Ansible `copy` + `no_log` + mode 0600) is reusable; the *content* (bearer tokens for a resource API) is application-specific and may not be needed at all — see [open-questions.md](open-questions.md). |
| `0002-service-framework-and-conventions.toml` | Flask app structure, translators, no-Pydantic | **Out** — application architecture. Only one fact crossed over: the choice between an `app.py:app` module object and a `create_app()` factory changes the gunicorn `ExecStart` line. Not re-read in full; the relevant fact is already captured in `deployment-architecture.md`. |

## Requirements — `requirements/operational.toml`

| ID | Title | Scope |
|---|---|---|
| REQ-OPS-001 | Reproducible deploy and destroy | **In** — direct precedent for a `sask-calendar` equivalent. |
| REQ-OPS-002 | Manual droplet access available | **In** — SSH + DO console fallback. |
| REQ-OPS-003 | Service runs as systemd unit | **In** — non-root user, restart policy, ownership. |
| REQ-OPS-004 | App tokens deployed from developer machine | **Partly in** — same caveat as ADR-0006 above. |
| REQ-SEC-001 (sask) | No secrets in repo | **In**, but note: `sask-calendar` already has its own `REQ-SEC-002` covering this; no new requirement needed, just confirm coverage. |

`requirements/functional.toml` was not read — it describes the resource
server's functional contract (auth, resource kinds), which is out of scope.

## PR specs — `prs/`

| File | Scope |
|---|---|
| `0001-scaffolding.toml` | **In**, lightly — confirms the "no GitHub Actions / CI vendor" decision and the spec-driven workflow that produced everything else. |
| `0003-droplet-provisioning.toml` | **In, heavily** — this is the OpenTofu PR spec; scope/out-of-scope/acceptance/notes-for-assistant sections are the closest existing analogue to what a `sask-calendar` provisioning SPEC should contain. |
| `0004-service-deployment.toml` | **In, heavily** — the Ansible PR spec; same reuse value as above for configuration management. |
| `0002-local-resource-service.toml` | **Out** — the Flask resource server itself. Not read. |

## Infrastructure as code — `infra/`

All `.tf` files are **in scope**: `versions.tf`, `variables.tf`, `main.tf`,
`ssh-config.tf`, `outputs.tf`, `terraform.tfvars.example`, `.gitignore`. These
define every cloud resource (SSH key, droplet, reserved IP + assignment, DNS
record, firewall) and the generated local SSH config snippet. Fully
deployment-mechanical; nothing functional in here.

## Configuration management — `ansible/`

All files **in scope**: `ansible.cfg`, `inventory.yml`, `site.yml`,
`group_vars/all.yml`, and the three roles (`base`, `sask_service`, `caddy`).

Within the `sask_service` role, one task is application-specific in its
*content* but not its *pattern*: "Sync `src/sask` package" and "Copy
resources" move `sask`'s own application code and assets. The **pattern**
(rsync-based code sync, systemd unit templating, environment-file templating)
is what ports; the specific paths (`src/sask/`, `resources/`) get re-pointed
at `sask-calendar`'s own `src/sask/`, `resources/`, and — new, not present in
`sask` — `config/` (see [porting-plan.md](porting-plan.md)).

## Orchestration scripts — `scripts/`

All **in scope**: `provision.sh`, `destroy.sh`, `connect.sh`, `deploy.sh`,
`export-requirements.sh`. `acceptance-test.sh` is **partly in scope** — its
preflight/pass-fail/curl structure ports directly; its specific assertions
(image/json/audio content types, byte-identity of a `splash.png`) are
application-specific and would need to be re-authored against whatever
`sask-calendar`'s deployed page actually returns.

`run-local.sh`, `run-tests.sh`, `dev-shell.sh`, `devlog-entry.sh` were listed
but not read in depth — they're dev-workflow conveniences with
`sask-calendar` equivalents already in `tools/` (`start_web.sh`,
`run-tests.sh`, `pre-commit-check.sh`).

## Tests — `tests/`

| Path | Scope |
|---|---|
| `tests/acceptance/conftest.py` | **In, pattern only** — session-scoped fixtures reading a local secrets file and exposing a `base_url`. The token-reading fixture is conditional on whether the port needs application auth at all (see open-questions.md). |
| `tests/acceptance/test_remote.py` | **Partly in** — `test_health_returns_200`, `test_tls_certificate_is_valid` structurally port as-is. The resource-kind tests (image/json/audio status + content-type + byte-identity) are application-specific and excluded. |
| `tests/test_auth.py`, `test_health.py`, `test_resources.py` | **Out** — unit tests against the Flask resource server. Not read. |
| `tests/results/PR-003*.{md,txt}`, `tests/results/PR-004.md` | **In** — these are the evidence trail for the provisioning and deployment PRs: acceptance checklists, live-apply timing, idempotency double-run output, kill/restart timing, full destroy→reprovision→redeploy cycle. This is the single best template for what a `sask-calendar` `tests/results/SPEC-0XX.md` should look like for the equivalent work. |

## Docs and narrative — `docs/`

| File | Scope |
|---|---|
| `docs/notes/lessons.md` | **In, heavily** — a full retrospective written after PR-004, including a section ("Applying these lessons to a production gaming app") that already extrapolates the pattern beyond the hobby-scale original. The "per-PR implementation notes" section is effectively a pre-written pitfalls list; reproduced and adapted in `deployment-architecture.md`. |
| `docs/devlog.md` | **In** — reverse-chronological log entries for PR-003 and PR-004 corroborate and add minor timing/sequencing detail beyond `lessons.md` (e.g. exact destroy/provision resource counts and durations, the now-superseded manual-DNS step that was later replaced by Tofu-managed DNS). |
| `docs/references.md` | Not read — general links, not deployment-specific. |

## `sask-calendar` anchors cross-checked

Not part of `sask`, but the existing hooks in `sask-calendar` that this
analysis is meant to feed, confirmed present during this review:

- `design/decisions/dd-0001-scaffolding.toml` and `dd-0003-ux-and-service.toml`
  followups (both name the deferred DO deploy/destroy/redeploy DD).
- `design/specs/spec-005-ux-mvp.toml` ("reusing the sask deploy pattern").
- `design/reqs/req-ops-003.toml` (reserves `/scripts` in the agreed tree;
  not yet created — `ls` confirms no `scripts/` directory exists today).
- `design/reqs/req-sec-001.toml`, `req-sec-002.toml` (dev-VM SSH hardening
  and secrets-in-repo exclusion — already in place, already mirrors
  `sask`'s ADR-0001 policy almost exactly).
- `ansible/` exists today as an empty placeholder (`.gitkeep` only) —
  ready to receive the ported roles.
- `infra/configuration.nix` exists today but is the **dev VM's** NixOS
  config, a different concern from `sask`'s `infra/*.tf` (production cloud
  IaC) — see the layout recommendation in `porting-plan.md`.
- `wsgi.py` already exposes `app = create_app()` at module level, which
  simplifies the gunicorn `ExecStart` relative to `sask`'s experience (see
  `deployment-architecture.md`'s pitfalls log, item on app-factory vs
  module-level `app`).
