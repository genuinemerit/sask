# Deploy-port implementation plan

**Status: current.** Written 2026-06-21 at the end of a review/planning
session, self-contained so a session opened only within `sask-calendar` (no
access to the sibling `~/Code/sask` repo) has everything needed to start
implementing. Authoritative design docs are
[DD-0014](../design/decisions/dd-0014-deploy.toml),
[SPEC-022](../design/specs/spec-022-tofu.toml),
[SPEC-023](../design/specs/spec-023-ansible.toml),
[SPEC-024](../design/specs/spec-024-acceptance.toml), and
[REQ-OPS-013](../design/reqs/req-ops-013.toml)/
[014](../design/reqs/req-ops-014.toml)/
[015](../design/reqs/req-ops-015.toml)/
[REQ-SEC-003](../design/reqs/req-sec-003.toml) — this document is the
sequencing/checklist layer on top of those, not a replacement for reading
them.

## What this is

A hardened OpenTofu + Ansible + bash(`tools/`) harness to provision, deploy,
destroy, and redeploy `sask-calendar` on a DigitalOcean droplet, ported and
adapted from the now-retired sibling `sask` project's proven pattern. See
`source-inventory.md`, `deployment-architecture.md`, `testing-strategy.md`,
and `porting-plan.md` in this folder for the research this was built from —
all superseded in detail by the DD/SPECs above, but still useful background.

## Decisions made this session (2026-06-21)

1. **Execution order: SPEC-022 fully end-to-end, then SPEC-023, then
   SPEC-024.** SPEC-023's Ansible acceptance (`changed=0` on a second run,
   `config/` rendering correctly on a real host) structurally requires a
   droplet that only SPEC-022's Tofu creates — Ansible code can be drafted
   without a live target, but not verified. This overrides an initial
   instinct to do 023 before 022.
2. **No droplet-naming collision risk.** DD-0014 reuses `sask`'s exact
   droplet-side identity (`sask-*` DO resource names, `sask.davidstitt.net`
   DNS) on the theory that the original `sask` project's droplet is
   retired/destroyed. Confirmed directly with the user: it was destroyed
   out-of-band after that project's last devlog entry. A cheap
   `doctl`/DO-console sanity check before the first real `tofu apply` is
   still worth doing (see pre-flight checklist) but isn't expected to find
   anything.
3. **Add a minimal `/health` route.** `src/sask/web/routes.py` currently has
   only `/`, `/moons`, `/planets`, `/sky`, `/ephemeris`, `/ephemeris/download`
   — no health endpoint. SPEC-024's acceptance checks were deliberately
   phrased as "root (or `/health`, if added)" to leave this open; decided to
   add one, for kill/restart and acceptance checks that shouldn't depend on
   engine/config state rendering correctly.
4. **`/tools`, not `/scripts`, for orchestration.** `sask`'s own layout (and
   this folder's original research) used a `scripts/` directory, but
   `sask-calendar`'s actual convention is `/tools`, where orchestration
   scripts already live. **Corrected throughout DD-0014 and
   SPEC-022/023/024** (and in this plan) to land all new orchestration scripts
   in `tools/` instead, alongside the existing `pre-commit-check.sh`,
   `start_web.sh`, `run-tests.sh`. Note: `REQ-OPS-003` (from `DD-0001`, already
   `accepted`) still lists `/scripts` in "the agreed tree" — that line is
   stale but not enforced by any validator (`tools/validate_specs.py` only
   checks TOML schema, not directory existence), and was deliberately left
   unedited as outside today's scope. Flag it for a future scaffolding
   cleanup if it bothers you.

## Facts established by code review (no need to re-derive)

- **`config/` path resolution already works, no new mechanism needed.**
  `src/sask/web/__init__.py:18-20` resolves `config_dir` via
  `Path(__file__).resolve().parent.parent.parent.parent` — a pure
  file-relative walk-up from the package's own installed location, not an
  env var, not CWD-relative. As long as the Ansible `app` role places
  `config/` as a sibling of `src/` under `/opt/sask/` (mirroring the repo's
  own `<root>/src/sask/web/__init__.py` + `<root>/config/` layout), resolution
  holds regardless of the systemd unit's `WorkingDirectory`. Templates resolve
  the same way, one level shallower (`parent.parent` from the same file, to
  `src/sask/templates/`) — already carried by the `src/sask` rsync, no
  separate task needed.
- **`resources/` is currently empty** (`resources/.gitkeep` only; no app code
  references it) — unlike `sask`'s own `resources/`, which held real served
  assets. SPEC-023's `app_role` deliverable correctly does **not** list a
  `resources/` sync task. No action needed unless/until something is added
  there later.
- **`wsgi.py` already does the simple thing.** `from sask.web import
  create_app; app = create_app()` at module level — gunicorn's `ExecStart`
  targets `wsgi:app` directly, no `create_app()` factory-string ambiguity
  (`sask` itself had to work this out the hard way; not an issue here).
  `README.md`'s documented manual invocation
  (`PYTHONPATH=src .venv/bin/gunicorn wsgi:app`) already matches.
- **`flake.nix` is missing the tooling this work needs.** Currently only
  `python312, poetry, ruff, sqlite`. `sask`'s own `flake.nix` additionally had
  `opentofu, ansible, ansible-lint, openssh, jq, curl, gh` — all needed here
  too, plus `xcaddy` (new — for the rate-limit-plugin Caddy build, which
  `sask` didn't need). This is an implicit first task, not spelled out as a
  deliverable in any SPEC.
- **The rate-limited route is `/ephemeris/download`** (confirmed in
  `src/sask/web/routes.py`) — the "expensive public ephemeris endpoint" that
  REQ-SEC-003 and SPEC-023's `caddy_role` need a tighter per-IP limit on than
  the interactive pages.

## Pre-flight checklist (before any real cloud action)

- [ ] Add `opentofu`, `ansible`, `ansible-lint`, `openssh`, `jq`, `curl`,
      `gh`, `xcaddy` to `flake.nix`'s devShell; confirm `nix develop` enters
      cleanly with all of them on PATH.
- [ ] Confirm `~/.config/sask/infra.env` exists (outside the repo) exporting
      `DIGITALOCEAN_TOKEN`, per the secrets policy in `secrets/README.md` /
      REQ-SEC-002. Create `secrets/infra.env.example` in-repo as the template
      (real file stays out of git).
- [ ] Sanity-check via `doctl` or the DO web console that no `sask-*`
      droplet/reserved-IP/firewall/SSH-key resources and no
      `sask.davidstitt.net` DNS record remain from the original `sask`
      project, before the first `tofu apply` under the reused identity.
- [ ] Confirm an SSH key pair exists at the path `infra/tofu/variables.tf`
      will reference (per `sask`'s precedent, typically
      `~/.ssh/id_ed25519.pub` or project-specific) and is already registered
      for the developer's own access.

## Phase 1 — SPEC-022: droplet provisioning (OpenTofu)

Implement, apply for real, and verify before starting SPEC-023.

**Files to create:**
- `infra/tofu/versions.tf` — `digitalocean ~>2.0`, `http`, `local` providers.
- `infra/tofu/variables.tf` — region (`fra1`), size (`s-1vcpu-1gb`), image
  (`ubuntu-24-04-x64`), SSH key path, domain.
- `infra/tofu/main.tf` — `digitalocean_ssh_key`, `digitalocean_droplet` (no
  cloud-init), `digitalocean_reserved_ip` + `_assignment`,
  `data "digitalocean_domain"` lookup (fails fast at plan time if
  `davidstitt.net` isn't DO-nameservered) + `digitalocean_record` (A record
  for `sask.davidstitt.net` → reserved IP), `digitalocean_firewall` (22 from
  developer's current IP via the `http` data source `/32`; 80/443 from
  anywhere; egress open).
- `infra/tofu/ssh-config.tf` — `local_file` writing
  `~/.ssh/config.d/sask` (mode 0600, `Host sask-droplet` → reserved IP).
- `infra/tofu/outputs.tf` — reserved IP, droplet ID, next-steps.
- `infra/tofu/terraform.tfvars.example`, `infra/tofu/.gitignore` (state,
  lock file, real tfvars).
- `tools/provision.sh` — source `infra.env`, `cd infra/tofu`,
  `tofu init -upgrade && tofu apply [$AUTO]`, `-y` flag support.
- `tools/destroy.sh` — same sourcing, sequences reserved-IP-assignment
  detach **before** `tofu destroy` (a droplet can't be destroyed while a
  reserved IP is assigned to it — confirmed in `sask`'s own destroy timing
  log, ~12s detach + ~21s destroy, sequential not parallel).

**Acceptance (from SPEC-022, verify with evidence):**
- `tofu apply` creates every resource; DNS resolves to the reserved IP;
  firewall exposes 22 (dev IP) and 80/443 (any).
- `tofu destroy` detaches the reserved IP first, removes
  `~/.ssh/config.d/sask`.
- A destroy/recreate cycle gives the droplet a new ephemeral IP while the
  reserved IP (and thus DNS + SSH alias) stays unchanged.
- No token in any `.tf` file or in Tofu state.
- Re-running `provision.sh` is a ~10s no-op except when the developer's IP
  changed (firewall rule updates).

**Evidence:** `tests/results/SPEC-022.md` (checklist + timing), with raw
output in sibling `tests/results/SPEC-022-provision.txt` /
`-destroy.txt` if too long for the table. Flip `SPEC-022`'s `status` from
`"proposed"` to the project's in-progress/accepted convention once verified.

## Phase 2 — SPEC-023: service deployment (Ansible)

Only start once Phase 1's droplet is live and SSH-reachable at
`sask-droplet`.

**App-layer prep (do first, it's a small app change, not deploy plumbing):**
- Add a minimal `/health` route to `src/sask/web/routes.py` (decision #3
  above) — should not depend on engine/config rendering, just confirm the
  process is alive and responding.

**Files to create:**
- `ansible/ansible.cfg` — `host_key_checking = False`; relies on
  `~/.ssh/config`'s `Include ~/.ssh/config.d/*` (do **not** use an explicit
  `ssh_args = -F ~/.ssh/config.d/sask` — `~` isn't shell-expanded when
  Ansible invokes the SSH subprocess directly; this silently fails).
- `ansible/inventory.yml` — single host `sask-droplet`, referenced by SSH
  alias, never by IP.
- `ansible/site.yml` — runs `base`, `runtime`, `caddy`, `app` roles in order.
- `ansible/group_vars/all.yml` — all app-specific tunables: service name
  `sask`, synced directories, wsgi entry point, domain, gunicorn
  timeout/workers, rate-limit buckets, `apt_upgrade` boolean (default
  `false`).
- `ansible/roles/base/` — apt packages (`python3-venv`, `ca-certificates`,
  ...), non-root `sask` system user (no shell login), `/opt/sask` `/etc/sask`
  `/var/log/sask` owned by it, sshd hardening (`PermitRootLogin no`,
  `PasswordAuthentication no`, `PubkeyAuthentication yes`), unattended
  security upgrades. `cache_valid_time` on apt update; `apt upgrade` gated
  behind the `group_vars` boolean.
- `ansible/roles/runtime/` — Python venv, gunicorn, systemd unit template:
  `ExecStart` targets `wsgi:app` bound to `127.0.0.1`, request timeout +
  `max_requests` recycling, worker count sized for 1 vCPU, sandboxing
  (`NoNewPrivileges`, `ProtectSystem=strict`, `ProtectHome`, `PrivateTmp`,
  minimal `ReadWritePaths`). Environment file templated from `group_vars`.
  `WorkingDirectory` can be anything sane (e.g. `/opt/sask`) — confirmed
  above that `config/` resolution doesn't depend on it, only on `config/`
  being a sibling of `src/`.
- `ansible/roles/caddy/` — custom Caddy build via `xcaddy` including the
  rate-limit plugin (e.g. `github.com/mholt/caddy-ratelimit`); Caddyfile
  template (domain, `reverse_proxy` to localhost gunicorn, security headers:
  HSTS, `X-Content-Type-Options nosniff`, `frame-ancestors`,
  `Referrer-Policy`, a strict default CSP for a no-JS app; per-IP rate limit
  tighter on `/ephemeris/download` than the interactive pages; log path). No
  `caddy validate` as root in the play (it created a root-owned log file in
  `sask`'s own deploy, breaking Caddy's own write access afterward) — instead
  recurse-`chown` `/var/log/caddy` after the Caddyfile template task.
- `ansible/roles/app/` — `ansible.posix.synchronize` (rsync) `src/sask`
  (`--no-owner --no-group`, exclude `__pycache__`/`*.pyc` — plain `copy`
  re-copies pycache content and resets ownership, producing false "changed"
  every run); copy the `config/` data tree; copy `wsgi.py` to the app root
  (it isn't inside `src/sask/`, needs its own explicit task); `pip install`
  from a `requirements.txt` staged to a **remote** path first (Ansible's
  `pip` module needs a path that exists on the managed host, not the
  controller); application-secrets task stubbed (`copy` + `no_log: true` +
  mode 0600 against `secrets/sask.toml.example`, present but unused since
  auth is deferred); recurse-`chown` the app directory tree; restart handlers
  defined once, in fixed file order, so `daemon_reload` always precedes
  `restart` regardless of which task notified first.
- `tools/deploy.sh` — preflight (both `infra.env` and any local app-secrets
  file must exist, clear error + non-zero exit otherwise), re-export
  `requirements.txt`, source `infra.env`, `cd ansible && ansible-playbook
  site.yml`, `-y` to skip confirmation.
- `tools/connect.sh` — `exec ssh sask-droplet "$@"`.
- `tools/export-requirements.sh` — read `poetry.lock` + `pyproject.toml`
  directly via `tomllib` (Poetry 2.x has no built-in `export`), filtering
  dev/acceptance-only groups.
- `tools/redeploy.sh` — the single mainline act: calls `destroy.sh` →
  `provision.sh` → `deploy.sh` → the SPEC-024 verify step, in order,
  preserving the ordering guards from Phase 1 (reserved-IP detach,
  re-provision on IP change).

**Acceptance (from SPEC-023):** second consecutive deploy reports
`changed=0` across every task; service runs as non-root `sask` under
systemd with sandboxing directives present and effective, gunicorn on
`127.0.0.1`; Caddy serves valid TLS with the configured headers, rate limit
active and tighter on `/ephemeris/download`; sshd refuses root/password
auth, unattended upgrades enabled; a known computed value (e.g. a
`story_now` page field) renders correctly end-to-end on the droplet;
`redeploy.sh` runs the full chain as one invocation with ordering guards
intact; no secret in any Ansible log, only `.example` templates in the repo.

**Evidence:** `tests/results/SPEC-023.md`, same conventions as Phase 1.

## Phase 3 — SPEC-024: acceptance and operational test suite

Only meaningful once Phases 1 and 2 are both live and verified.

**Files to create:**
- `tools/acceptance-test.sh` — curl-based, `pass`/`fail` helpers, exits
  non-zero on first failure. Asserts: root (or `/health`) returns 200; TLS
  validates without `-k`; a rendered page contains an expected computed
  value (the deployed-pipeline analogue of `sask`'s byte-identity check —
  proof the whole chain DNS→TLS→Caddy→gunicorn→Flask→engine→template
  produced a real result).
- `tests/acceptance/conftest.py` — session-scoped `base_url` fixture (the
  deployed `https://` domain). No token/auth fixture (public app).
- `tests/acceptance/test_remote.py` — `test_health_returns_200`,
  `test_tls_certificate_is_valid`, using `requests` against the live
  service, not Flask's test client.
- Layer 4 operational tests, scripted where possible, recorded as evidence
  regardless:
  1. **Kill/restart** — kill the gunicorn process on the live droplet,
     confirm systemd restarts within the configured `RestartSec` window and
     the service responds correctly immediately after.
  2. **Idempotency** — run `tools/deploy.sh` twice consecutively against an
     already-converged droplet; bar is `changed=0` on the second run across
     every task.
  3. **Destroy → reprovision → redeploy from zero** — full cycle via
     `tools/redeploy.sh`, re-running Layers 2 and 3 against the fresh
     instance, recording before/after droplet IPs (proving the reserved-IP
     design held) and confirming the reserved IP/DNS/SSH alias survived
     unchanged.

**Evidence:** `tests/results/SPEC-024.md` — acceptance checklist, static
checks, a live-run section per apply/deploy with resource counts/timing, the
idempotency double-run, and the destroy/reprovision/redeploy section with
before/after IPs. Raw output too long for the table goes in sibling
`tests/results/SPEC-024-*.txt` files.

## Cross-reference

| DD/REQ | Implemented by |
|---|---|
| DD-0014 | SPEC-022, SPEC-023, SPEC-024 |
| REQ-OPS-013 (reproducible deploy/destroy/redeploy) | SPEC-022, SPEC-023 |
| REQ-OPS-014 (manual access + console fallback) | SPEC-022 |
| REQ-OPS-015 (systemd non-root service) | SPEC-023 |
| REQ-SEC-003 (deployment hardening) | SPEC-022, SPEC-023 |
