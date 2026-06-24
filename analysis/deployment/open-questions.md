# Open questions — decisions for the user before drafting DD/REQ/SPEC

**RESOLVED (2026-06-21).** All nine questions below are answered in
[DD-0014](../design/decisions/dd-0014-deploy.toml)'s decision section. Kept
here as the historical record of the questions as originally posed; see
[deploy-port-plan.md](deploy-port-plan.md) for the current plan.

These can't be resolved by reading code; they're choices, not facts. Listed
roughly in the order they'd block drafting work.

## 1. Droplet-side naming — reuse `sask` or choose a distinct identifier?

`sask-calendar`'s Python package is already named `sask` (`src/sask/`),
identical to the *other* project's package name. `sask`'s deployment pattern
hardcodes that name throughout the droplet side: system user `sask`,
`/opt/sask`, `/etc/sask`, `/var/log/sask`, `sask.service`, DO resource prefix
`sask-*`, SSH alias `sask-droplet`.

**Recommendation:** pick a distinct droplet-side identifier (e.g. `saskcal`)
for the system user, directories, systemd unit, DO resource prefix, and SSH
alias — independent of whether the Python package itself stays named
`sask`. This avoids any ambiguity or literal collision if both projects are
ever deployed under the same DO account, even to separate droplets.

- [ ] Confirm distinct droplet-side name, or confirm reuse of `sask` is
      acceptable (e.g. because the original `sask` droplet will never
      coexist with this one).

## 2. Does the web UI need authentication?

`sask`'s service required bearer-token auth for every resource it served —
that's the application contract this analysis was scoped to exclude.
`sask-calendar`'s `DD-0003` describes a server-rendered Jinja UI with no
mention of access control. Whether the deployed calendar app should be:

- Fully public (no auth at all) — simplest; no application-secrets category
  needed, ADR-0006's mechanism becomes irrelevant rather than ported.
- Behind some access control (shared secret, basic auth via Caddy, etc.) —
  if so, the `copy` + `no_log` + mode-0600 Ansible pattern from
  `deployment-architecture.md` is the right mechanism to reuse, scaled down.

This determines whether `secrets/` gains a second category template at all,
and whether `tests/acceptance/conftest.py` needs a token fixture.

- [ ] Public, no auth — or — needs access control (specify mechanism).

## 3. Domain name

`sask` used `sask.davidstitt.net` (a subdomain of an existing
DO-nameservered zone). What should the calendar app's domain/subdomain be?
This also determines whether the existing `data "digitalocean_domain"`
lookup in `main.tf` can be reused as-is (same parent zone) or needs a
different zone name.

- [ ] Subdomain choice (e.g. `calendar.davidstitt.net`,
      `sask-calendar.davidstitt.net`, or other).

## 4. Separate droplet, or share infrastructure with the existing `sask` project?

ADR-0004's "single droplet, single service" topology is simple specifically
*because* it's single-purpose. Sharing a droplet between two services adds
real complexity (two systemd units, one Caddy config routing by domain
instead of one Caddyfile per droplet, shared firewall surface, shared
blast radius on destroy).

**Recommendation:** a separate droplet, mirroring `sask`'s topology
unchanged — same simplicity argument that motivated it the first time.

- [ ] Separate droplet (recommended) — or — share the existing droplet
      (specify reasoning, e.g. cost).

## 5. Tofu state — local again, or remote from day one this time?

`sask`'s ADR-0003 chose local state deliberately for a single-developer
hobby project, with a documented migration path if that ever stopped being
acceptable. Nothing about `sask-calendar`'s situation changes that
calculus — still single-developer, still hobby-scale — but worth asking
explicitly rather than defaulting silently to the same call.

- [ ] Local state again (recommended, matches precedent) — or — remote state
      from the start (specify backend, e.g. DO Spaces).

## 6. Shared or separate local secrets paths?

`sask` reads infra credentials from `~/.config/sask/infra.env` and app
secrets from `~/.config/sask/tokens.toml`. If the port's droplet-side name
is distinct (per question 1), the natural local path is
`~/.config/<that-name>/infra.env`, fully separate from `sask`'s. Confirms
independent provision/destroy cycles can't accidentally cross-affect each
other via a shared credentials file.

- [ ] Confirm separate `~/.config/<name>/` path (default: yes, once question
      1 is resolved).

## 7. Region and droplet sizing — reuse `fra1` / `s-1vcpu-1gb`, or resize?

`sask-calendar` has measured performance budgets already (REQ-OPS-010): an
ephemeris sweep worst case targets 3–5s, "re-validated on the deployment
target." Whether `s-1vcpu-1gb` is adequate for that workload under gunicorn
(vs. `sask`'s trivial static-resource-serving load) is worth a deliberate
check rather than inheriting the size by default.

- [ ] Reuse `s-1vcpu-1gb`/`fra1` as a starting point and re-measure once
      deployed (recommended — REQ-OPS-010 already calls for
      deployment-target re-validation) — or — start larger.

## 8. Layout: `infra/tofu/` subdirectory, or flat `infra/`?

See `porting-plan.md`'s reasoning for recommending `infra/tofu/` to keep the
dev-VM's `configuration.nix` conceptually separate from the production
droplet's Tofu files. This is a recommendation, not a forced choice.

- [ ] `infra/tofu/` (recommended) — or — flat `infra/` alongside
      `configuration.nix`.

## 9. Split into two SPECs (provisioning / service deployment) or one?

`sask` split PR-003 (Tofu) and PR-004 (Ansible) into separate PR specs,
which let each be reviewed, tested, and have its own `tests/results/` entry
independently. `porting-plan.md` suggests mirroring that split. Confirm
before drafting.

- [ ] Two SPECs (recommended, matches precedent) — or — one combined SPEC.
