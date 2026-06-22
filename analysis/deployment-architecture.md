# Deployment architecture — as built in `sask`

Three layers, each independently re-runnable and idempotent, each owned by a
different tool, each invoked only through a thin orchestration script. No
GitHub Actions, no CI vendor — every command in this document runs from the
developer's machine via `nix develop`.

```
scripts/*.sh        orchestration   (bash; preflight checks, env sourcing, -y flag)
   |
   v
infra/*.tf           IaC layer       (OpenTofu; cloud resources, declarative)
   |
   v
ansible/*            config layer    (Ansible; droplet state, declarative, idempotent)
```

Tofu answers "what cloud resources exist." Ansible answers "what does the
droplet look like once it exists." Scripts answer "in what order, with what
guardrails, do I run those two tools." None of the three knows how to do the
others' job, and that separation is what makes each layer independently
testable and re-runnable.

## Layer 1 — Infrastructure as code (OpenTofu)

Source: `sask/infra/{versions,variables,main,ssh-config,outputs}.tf`.

**Provider.** `digitalocean` (`~> 2.0`), plus two small utility providers:
`http` (fetch the developer's current public IP at apply time) and `local`
(write a generated SSH config snippet to disk). `DIGITALOCEAN_TOKEN` is read
automatically from the environment — no token ever appears in `.tf` files.

**Resources created, every `apply`:**

| Resource | Purpose |
|---|---|
| `digitalocean_ssh_key` | Registers the project's SSH public key with DO. |
| `digitalocean_droplet` | The Ubuntu 24.04 VM (`s-1vcpu-1gb`, region `fra1`). No cloud-init — Ansible owns all configuration. |
| `digitalocean_reserved_ip` + `_assignment` | A stable IP that survives droplet destroy/recreate. This is the load-bearing design choice — see below. |
| `digitalocean_record` | DNS A record pointed at the **reserved IP**, not the droplet. Requires the domain to already be DO-nameservered; a `data "digitalocean_domain"` lookup fails fast at plan time if it isn't. |
| `digitalocean_firewall` | Inbound 22 from the developer's current IP only (via the `http` data source + `/32` CIDR); inbound 80/443 from anywhere (needed for Let's Encrypt + the live service); outbound open. |
| `local_file` | Writes `~/.ssh/config.d/<project>` (mode 0600) with a `Host <project>-droplet` alias pointing at the reserved IP. Destroyed by `tofu destroy`. |

**Why the reserved IP matters.** Every destroy/reprovision cycle assigns the
droplet a new ephemeral direct IP — confirmed in `sask`'s own test logs
(`46.101.229.123` → next cycle a different address entirely). Because the
DNS record and the SSH config alias both point at the *reserved* IP, neither
needs to change across that cycle. This is the single biggest reason the
destroy→reprovision→redeploy loop requires zero manual steps. Port this
choice unchanged.

**State.** Local (`infra/terraform.tfstate`, gitignored). Accepted trade-off
for a single-developer hobby project (ADR-0003): zero setup cost, but state
loss means orphaned cloud resources requiring manual cleanup via the DO web
console. The documented migration path (DO Spaces remote backend,
`tofu init -migrate-state`) is deferred until/unless that risk becomes real.

**DNS evolution worth noting.** `sask`'s devlog shows DNS was *originally* a
manual GoDaddy step, then moved into Tofu (`digitalocean_record`) once the
domain was confirmed DO-nameservered. Start the port with DNS in Tofu from
day one — there's no reason to repeat the manual-step detour.

## Layer 2 — Configuration management (Ansible)

Source: `sask/ansible/{ansible.cfg,inventory.yml,site.yml,group_vars/all.yml}`
plus three roles: `base`, `sask_service`, `caddy`.

**Inventory** references the host by the SSH alias from layer 1
(`sask-droplet`), never by IP — this is what makes the playbook itself
immune to the IP changing on redeploy. `ansible.cfg` sets
`host_key_checking = False` and relies on the main `~/.ssh/config`'s
`Include ~/.ssh/config.d/*` directive rather than an explicit `-F` flag (see
pitfalls below for why the explicit flag doesn't work).

**`base` role** — OS prep that doesn't change per-deploy: apt packages
(`python3-venv`, `ca-certificates`, etc.), a non-root system user with no
shell login, and the three top-level directories (`/opt/<svc>`,
`/etc/<svc>`, `/var/log/<svc>`) with correct ownership. `apt upgrade` is
gated behind a `group_vars` boolean (default `false`) — deliberately not run
on every deploy.

**`<service>` role** — the actual deploy:
1. Copy `requirements.txt` to the droplet, then `pip install` into a venv
   *from that remote path* (the pip module needs a path that exists on the
   managed host, not the controller — see pitfalls).
2. `ansible.posix.synchronize` (rsync) the application source into place,
   excluding `__pycache__`/`*.pyc`, with `--no-owner --no-group` so rsync
   doesn't fight Ansible over file ownership on every run.
3. Copy any static config/resource directories the app needs at runtime.
4. Copy application secrets (if any) with the `copy` module — not
   `template` — mode 0600, and `no_log: true` on that task specifically.
5. Template the systemd unit and an environment file from `group_vars`.
6. Fix ownership of the whole app directory tree (`recurse: true`).
7. `daemon_reload`, enable, start. Handlers (defined once, in deterministic
   order) restart the service only when something that matters changed.

**`caddy` role** — apt repo + GPG key for Caddy, install, template a minimal
Caddyfile (domain + `reverse_proxy` + log path only — no manual TLS/ACME
directives, Caddy handles that itself), fix log directory ownership, enable
and start. Caddy auto-issues and auto-renews a Let's Encrypt certificate via
the `tls-alpn-01` challenge with zero manual steps, confirmed across both
the initial deploy and a from-zero redeploy in `sask`'s test logs.

**Why three roles, not one.** Each role has exactly one concern and its own
handler scope (Caddy's reload handler lives in the `caddy` role; the
service's restart handler lives in the service role). This made it possible
to re-run a single role in isolation while debugging — a concrete
operational benefit, not just tidiness.

## Layer 3 — Orchestration (bash scripts)

Source: `sask/scripts/*.sh`. Every script: `set -euo pipefail`, `cd` to repo
root first, source a project-specific env file from outside the repo before
doing anything cloud-facing, and accept a `-y` flag to skip the interactive
confirmation prompt (default is to prompt).

| Script | Does |
|---|---|
| `provision.sh` | Source `infra.env`, `cd infra`, `tofu init -upgrade && tofu apply [$AUTO]`. |
| `destroy.sh` | Same sourcing, `tofu destroy [$AUTO]`. |
| `connect.sh` | `exec ssh <project>-droplet "$@"` — trivial, but means the SSH alias is the *only* place an IP ever needs to be known. |
| `deploy.sh` | Preflight: both `infra.env` and the local app-secrets file must exist (clear error + non-zero exit if not). Re-export `requirements.txt`. Source `infra.env`. `cd ansible && ansible-playbook site.yml`. |
| `export-requirements.sh` | Reads `poetry.lock` + `pyproject.toml` directly with a small inline Python script, rather than `poetry export` — Poetry 2.x moved `export` to a plugin not present in the Nix shell. Filters out dev/acceptance-only groups. |
| `acceptance-test.sh` | curl-based smoke test against the live HTTPS endpoint; `pass`/`fail` helpers, exits non-zero on first failure. |

The preflight-check pattern in `deploy.sh` (fail loud and early if a
required local secret is missing, before touching the network) is worth
preserving verbatim — it's a cheap guard against the most common deploy
failure mode.

## Secrets policy

Two categories, never overlapping, neither ever in git (ADR-0001):

1. **Infrastructure credentials** (DO API token, SSH key paths) — live in
   `~/.config/<project>/infra.env`, outside the repo, sourced as env vars by
   `provision.sh`/`destroy.sh`/`deploy.sh` via `set -a; source ...; set +a`.
2. **Application secrets** (if any exist for the deployed app) — a local
   file outside the repo, deployed to the droplet by Ansible's `copy`
   module with `no_log: true` and mode 0600. The repo holds only a
   `secrets/<name>.toml.example` template.

Neither category ever touches Tofu state or an Ansible log line. `sask`'s
test evidence (`git grep` for token values, Tofu state inspection) confirms
this held in practice, not just on paper.

## Idempotency — the concrete techniques that made it real

This is the most transferable part of the whole pattern. "Idempotent" is
easy to claim and hard to deliver; these are the specific choices that
delivered it, each one tied to a problem `sask` actually hit:

| Technique | Problem it solves |
|---|---|
| `ansible.posix.synchronize` (rsync) instead of `ansible.builtin.copy` for source trees | `copy` re-copied `__pycache__`/`.pyc` content (which varies between identical runs) and reset file ownership via rsync's implicit `-o` flag — both produced false "changed" on every run. `--exclude=__pycache__ --no-owner --no-group` fixed it. |
| Copy `requirements.txt` to a remote path before `pip install -r` | Ansible's `pip` module's `requirements:` argument must point at a path on the *managed host*, not the controller. |
| Remove `caddy validate` from the deploy path; recurse-`chown` `/var/log/caddy` after the Caddyfile template task | Running `caddy validate` as root during the play created `sask.log` owned `root:root`; Caddy (running as its own system user) then couldn't write to its own log directory afterward. |
| Rely on `~/.ssh/config`'s `Include ~/.ssh/config.d/*` rather than `ssh_args = -F ~/.ssh/config.d/<project>` in `ansible.cfg` | `~` is not shell-expanded when Ansible invokes the SSH subprocess directly; the explicit `-F` flag silently failed to resolve. |
| `cache_valid_time` on the apt-update task; `apt_upgrade` gated behind an explicit `group_vars` boolean (default `false`) | Keeps repeat deploys fast and prevents surprise package upgrades as a side effect of an unrelated deploy. |
| Handlers defined once, in a fixed file order, notified rather than called directly | Guarantees `daemon_reload` always runs before a service restart when both are triggered by the same unit-file change, regardless of which task notified first. |
| DNS record attached to the **reserved IP**, never the droplet directly | Removes DNS from the set of things that need to change across a destroy/recreate cycle — see layer 1. |

The end state `sask` reached and verified twice (initial convergence, then
again after a full destroy+reprovision): re-running `deploy.sh -y` against
an already-converged droplet reports `changed=0` across every task. That is
the bar to hold the port to — not "the script runs without erroring," but
"the second run changes nothing."

## Pitfalls log — what to pre-empt, not rediscover

These are `sask`'s `docs/notes/lessons.md` "PR-004 implementation notes,"
condensed to the fixes. Most are Ansible/SSH/Poetry mechanics that will
recur verbatim in the port unless deliberately avoided:

1. **App factory vs module-level `app` object changes the gunicorn
   `ExecStart`.** `sask` used `create_app()`, which meant
   `gunicorn 'sask.app:create_app()'`, not `gunicorn 'sask.app:app'` as
   originally planned. `sask-calendar`'s `wsgi.py` already resolves this at
   module level (`app = create_app()`), so the port's `ExecStart` should
   target `wsgi:app` directly — simpler than `sask` had it. Confirm in the
   porting plan rather than assuming.
2. **Poetry 2.x has no built-in `export`.** Read `poetry.lock` +
   `pyproject.toml` directly with `tomllib` rather than depending on
   `poetry-plugin-export` being present in the Nix shell.
3. **DigitalOcean renamed "Floating IP" to "Reserved IP" in 2022.** Tutorials
   and older docs may still reference `digitalocean_floating_ip`; the
   current provider resource is `digitalocean_reserved_ip` /
   `digitalocean_reserved_ip_assignment`.
4. **The SSH-allowed-IP firewall rule is fixed at apply time.** If the
   developer's IP changes between sessions (mobile, VPN, ISP rotation),
   re-running `provision.sh` (a ~10s no-op for everything else) is required
   to regain SSH access. Not a bug, but worth documenting up front so it
   isn't mistaken for one.
5. **A droplet can't be destroyed while a reserved IP is still assigned to
   it.** `sask`'s destroy timing log shows IP-assignment detach and droplet
   destroy running sequentially (~12s + ~21s) because of this dependency —
   expected, not a sign of drift.

## Sizing/topology choices made, available to reuse or revisit

From ADR-0004, all explicit, all revisitable for the port (see
`open-questions.md`):

- Single droplet, no load balancer, no Kubernetes, no App Platform —
  deliberately chosen to learn/control the "classic VM" layer directly.
- `s-1vcpu-1gb`, region `fra1`, image `ubuntu-24-04-x64`.
- Root user only on the droplet itself is *not* carried forward — `sask`
  moved to a non-root system user for the deployed service starting in the
  Ansible PR; the port should do the same from the start.
- ufw was deliberately *not* added — the DO cloud firewall was judged
  sufficient at this scale, with ufw as a documented future hardening step
  if the threat model changes.
