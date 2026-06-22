# Porting plan — concrete adaptation of `sask`'s deploy pattern

**Status (2026-06-21): superseded.** This was the brief drafting DD-0014 and
SPEC-022/023/024 worked from. Two of its calls didn't survive: it assumed a
new `/scripts` directory (sask-calendar's actual convention is `/tools`,
corrected throughout the DD/SPECs and in `deploy-port-plan.md`), and its
"naming collision" section below predates DD-0014's decision to reuse `sask`
outright. The directory mapping, ID mapping, and technical-adaptation facts
(gunicorn `ExecStart`, directories to sync) are still accurate and kept for
reference. See [deploy-port-plan.md](deploy-port-plan.md) for the current plan.

This is the actionable layer: a file-by-file mapping, the naming changes the
port needs, and a skeleton of the design documents this should eventually
become. None of this has been drafted into `/design` — it's the brief a
future SPEC-drafting session (or Claude Code implementation session) should
start from. Resolve [open-questions.md](open-questions.md) first; several
items below depend on those answers.

## Directory and file mapping

| `sask` source | `sask-calendar` target | Notes |
|---|---|---|
| `infra/{versions,variables,main,ssh-config,outputs}.tf` | `infra/tofu/*.tf` (new subdirectory — see below) | Not flat into `infra/`. |
| `infra/terraform.tfvars.example`, `infra/.gitignore` | `infra/tofu/...` | Same. |
| `ansible/*` | `ansible/*` | Direct — the directory already exists (currently just `.gitkeep`). |
| `scripts/{provision,destroy,connect,deploy,export-requirements}.sh` | `tools/*.sh` | **Corrected 2026-06-21:** not `scripts/*.sh` — sask-calendar's convention is `/tools` (REQ-OPS-003 lists `/scripts` but it's never been created; existing orchestration scripts like `pre-commit-check.sh` already live in `/tools`). |
| `scripts/acceptance-test.sh` | `tools/acceptance-test.sh` | Port structure; rewrite assertions per `testing-strategy.md`. |
| `tests/acceptance/{conftest.py,test_remote.py}` | `tests/acceptance/{conftest.py,test_remote.py}` | New directory under existing `tests/`. |
| `secrets/README.md` policy | already present, already matches | `sask-calendar/secrets/README.md` already states the same `.example`-only git policy (REQ-SEC-002). Add `secrets/infra.env.example` (new) when drafted; an application-secrets template only if open-questions resolves toward needing one. |
| `decisions/000N-*.toml` (ADR-XXXX) | `design/decisions/dd-00NN-*.toml` (DD-XXXX) | Schema differs slightly — see ID mapping below. |
| `requirements/operational.toml` entries | `design/reqs/req-ops-0NN.toml` (one file per requirement) | `sask-calendar`'s schema is one requirement per file, not one array-of-tables file like `sask`'s `requirements/operational.toml`. |
| `prs/000N-*.toml` (PR-NNN) | `design/specs/spec-0NN-*.toml` (SPEC-NNN) | See ID mapping below. |

### Why `infra/tofu/`, not a flat `infra/`

`sask-calendar`'s `infra/` already means something specific:
`infra/configuration.nix`, the **dev VM's** NixOS machine config (per
CLAUDE.md's "Machine / project split" — `infra/configuration.nix` is "canonical
full replacement for `/etc/nixos/configuration.nix` on the sask-dev VM").
`sask`'s `infra/` meant something different: production cloud IaC, because
`sask` had no separate dev-VM concept (its dev environment was just a Nix
devShell on the developer's existing Ubuntu host).

Dropping `.tf` files straight into `sask-calendar/infra/` next to
`configuration.nix` would conflate "the dev machine's config" with "the
production droplet's IaC" — two different machines, two different
lifecycles, one of them version-controlled-and-applied-by-hand, the other
fully scripted. A subdirectory (`infra/tofu/`, or `infra/do/` if a more
provider-neutral name is preferred) keeps the existing machine/project split
intact and extends it rather than blurring it. This is a recommendation, not
a forced choice — flagged in open-questions.md if a flat layout is
preferred instead.

## ID and naming mapping

| `sask` concept | `sask-calendar` equivalent | Notes |
|---|---|---|
| `ADR-XXXX` | `DD-XXXX` | Next free ID at time of drafting — currently `DD-0013` is the highest in use, so the deploy DD would likely be `DD-0014`. Confirm against `design/decisions/` at drafting time, not against this document. |
| `REQ-OPS-XXX` (sask numbering, 1–4) | `REQ-OPS-0XX` continuing `sask-calendar`'s own sequence | Currently `REQ-OPS-012` is the highest in use; new requirements continue from there. Confirm at drafting time. |
| `PR-XXX` | `SPEC-0XX` | Currently `SPEC-021` is the highest in use. |
| `prs/_schema.toml` field shape (`scope.in`/`scope.out`, `deliverables.files`/`.tests`, `acceptance.items`, `review.focus`/`.smoke_test`, `notes.for_assistant`) | `design/specs/_schema.toml` requires `implements`, `scope`, `deliverables`, `acceptance` sections | The two schemas are close but not identical — `sask-calendar`'s spec schema doesn't have a formally required `review` or `notes` section, though existing specs (e.g. `SPEC-001`) use both anyway as convention. Follow that existing convention for consistency. |

## Suggested document skeleton (not drafted here — this is a brief, not the work)

A future session should produce, in roughly this order:

1. **One DD** — "Hardened DO deploy/destroy/redeploy lifecycle" (closes the
   followup named in both DD-0001 and DD-0003). Context: the same
   "disposable host, durable state" philosophy already established for the
   *dev* VM (REQ-OPS-002) extended to the *production* droplet. Decision:
   adopt the three-layer OpenTofu/Ansible/scripts architecture described in
   `deployment-architecture.md`, including the reserved-IP + Tofu-managed-DNS
   choice and the non-root systemd service pattern. Alternatives section
   should cite the same rejected options `sask`'s ADR-0004 cited
   (multi-droplet+LB, DOKS, DO Functions, App Platform) since the same
   "classic VM, low ceremony, hobby scale" reasoning applies here.
2. **A handful of REQ-OPS items**, mirroring `sask`'s REQ-OPS-001/002/003
   (reproducible deploy/destroy, manual SSH+console fallback, systemd
   non-root service), and conditionally REQ-OPS-004's app-secrets pattern
   only if open-questions.md resolves toward needing application-level
   secrets at all.
3. **Two or three SPECs**, splitting the work the way `sask` did
   (provisioning vs. service deployment), since that split let each be
   reviewed and tested independently:
   - SPEC: droplet provisioning via OpenTofu.
   - SPEC: service deployment via Ansible (gunicorn + Caddy + systemd).
   - Possibly a third SPEC for the acceptance/operational test suite itself,
     if it's substantial enough to warrant separate review focus — `sask`
     folded this into the service-deployment PR instead; either split is
     defensible.

## Concrete technical adaptations already identified

These aren't open questions — they're facts established by reading
`sask-calendar`'s current code/config, ready to use directly when the SPECs
get drafted:

- **gunicorn `ExecStart`.** `sask-calendar/wsgi.py` already does
  `from sask.web import create_app; app = create_app()` — the factory is
  already resolved at module level. The systemd unit's `ExecStart` should
  target `wsgi:app` (e.g.
  `{{ venv_dir }}/bin/gunicorn wsgi:app --bind ... --workers ...`), matching
  the manual invocation already documented in `sask-calendar/README.md`
  (`PYTHONPATH=src .venv/bin/gunicorn wsgi:app`). This is simpler than what
  `sask` had to work out — no `app.py:app` vs `create_app()` ambiguity here,
  just confirm `PYTHONPATH=src` (or an installed package) is set correctly
  in the deployed environment file.
- **Directories to sync, beyond what `sask` synced.** `sask` only had
  `src/sask/` and `resources/` to move onto the droplet. `sask-calendar`
  also has `config/` — the externalized domain/lore data that REQ-OPS-006
  requires the engine to read from config rather than hardcode. The Ansible
  service role's task list needs a third sync/copy task for `config/`
  alongside the `src/sask/` rsync and the `resources/` copy.
- **`wsgi.py` itself** needs to land on the droplet too (it didn't exist as
  a separate file in `sask`'s pattern — `sask`'s ansible role synced
  `src/sask/` directly and pointed gunicorn at a module inside it). Add an
  explicit copy task for `wsgi.py` to the app directory root.
- **Template/static assets.** `src/sask/templates/` lives inside the
  package, so the existing `src/sask/` rsync task already carries it —
  no separate task needed, unlike `config/`.

## Verification needed before the SPEC can be written precisely

One item from `sask-calendar`'s own code wasn't traced in this session
(reading the engine's config-loading internals would cross into the
application-functional territory this analysis was scoped to avoid):

> **How does `src/sask` currently resolve the path to `config/` and
> `resources/` at runtime** — a path relative to the package/repo root, or
> an environment variable? `sask` used the latter for everything
> (`SASK_TOKENS_PATH`, `SASK_MANIFEST_PATH`, etc., all with defaults,
> overridable via the Ansible-templated environment file). If
> `sask-calendar` instead resolves these paths relative to the repo root or
> the package's own location, the deployed `WorkingDirectory` in the
> systemd unit must line up exactly with whatever that resolution assumes,
> or an environment-variable equivalent needs to be introduced. This is a
> five-minute check against `src/sask/` at the start of the actual
> implementation session — flagged here so it isn't skipped.

## Naming collision to resolve before drafting

`sask-calendar`'s Python package is `sask` (`src/sask/`, same as the
*other* project's package name). If the port reuses `sask`'s exact
droplet-side naming — system user `sask`, directories `/opt/sask`,
`/etc/sask`, systemd unit `sask.service`, DO resource prefix `sask-*` — it
collides head-on with anything already deployed under the original `sask`
project's pattern, even on a separate droplet (confusing at minimum; a real
collision if ever co-located). See `open-questions.md` for the naming
decision this depends on; nothing here should be drafted with the literal
string `sask` as the droplet-side identifier until that's resolved.
