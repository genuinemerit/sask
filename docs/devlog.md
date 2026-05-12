# sask — Development log

Reverse-chronological. Newest entries at top. Hand-written or auto-generated.

## 2026-05-12 — PR-003 first successful provision

`scripts/provision.sh` (interactive) completed cleanly. 7 resources created
in ~46s: SSH key and reserved IP in parallel (1s each), droplet (33s),
firewall and IP assignment in parallel (1s / 12s), ssh-config snippet last.
Reserved IP `206.189.249.29`; DNS A record for `sask.davidstitt.net` created
via `digitalocean_record` (TTL 300). `data.digitalocean_domain` correctly
verified the pre-existing `davidstitt.net` domain at plan time.
`~/.ssh/config.d/sask` written with 0600 permissions as designed.

Note: `provision.sh` runs `tofu init -upgrade` on every invocation. This
re-checks provider versions within constraints and is intentional — keeps
the lock file current. Slight overhead on repeat runs; not a problem.

Pending before PR-003 is complete: manual DO console inspection, SSH
connection test, destroy cycle, clean redeploy.

## 2026-05-12 — PR-003 implementation

Provisioned the DO droplet via OpenTofu. Created `infra/` with split .tf
files: versions, variables, main, ssh-config, outputs. Provider pinned to
`digitalocean ~> 2.0`. Droplet is `s-1vcpu-1gb` Ubuntu 24.04 in fra1.
Reserved IP attached for a stable address that survives destroy/apply
cycles. Cloud firewall restricts SSH (port 22) to the developer's current
IP fetched at apply time via the `http` data source; HTTP/HTTPS open from
anywhere. SSH config snippet written to `~/.ssh/config.d/sask` by
`local_file` resource (0600 permissions).

Note on terminology: DigitalOcean renamed "Floating IPs" to "Reserved IPs"
in 2022. The Tofu provider reflects this as `digitalocean_reserved_ip` /
`digitalocean_reserved_ip_assignment`. All documentation updated to match.

**Manual DNS step (required after each fresh provision):**
After `scripts/provision.sh` completes, the reserved IP is shown in the
`next_steps` output. Log into GoDaddy and set:

    A record: sask.davidstitt.net → <reserved IP>

DNS is not automated (GoDaddy has no Tofu provider worth using for a
single record). Once set, the record survives destroy/apply cycles because
the reserved IP persists. Only needed again if the reserved IP resource is
destroyed. Verify propagation with `dig +short sask.davidstitt.net` before
testing SSH.

Reference: PR-003, ADR-0003, ADR-0004, REQ-OPS-001, REQ-OPS-002.

## 2026-05-12 - PR-003 set up

NixOS guest clipboard sharing with host (virt-manager/QEMU/Spice)
Required in configuration.nix:

services.spice-vdagentd.enable = true;
services.qemuGuest.enable = true;
Explicit systemd user service for spice-vdagent (Plasma autostart wasn't picking it up).

Plasma Wayland session does NOT work — spice-vdagent's Wayland path expects Mutter's D-Bus interface (org.gnome.Mutter.DisplayConfig), which KDE/KWin doesn't provide. Solution: log in via Plasma X11 session and use spice-vdagent -x.
Set as default: services.displayManager.defaultSession = "plasmax11"; (verify exact name in your NixOS version).

Workflow: host-side browser (native Ubuntu) for Claude conversations,
NixOS VM for development. Clipboard flows freely. Resolution 1680x1050
in the VM stays performant on the XPS 13's integrated graphics.

SSH key for sask deployment: ed25519, project-specific
(~/.ssh/sask_ed25519), agent-loaded. Did NOT manually upload to DO —
OpenTofu will manage it as part of PR-003. ~/.ssh/config set up with
Include directive so PR-003 can drop a generated snippet into
~/.ssh/config.d/sask.

DO API token in ~/.config/sask/infra.env, exported as
DIGITALOCEAN_TOKEN (the convention the DO provider auto-detects).

## 2026-05-11 — PR-002 done

Built the local resource server: a Flask app that delivers authenticated
images, JSON, and audio over HTTP. Four real placeholder assets are served
(a splash image, a scenario JSON file, an MP3 ambient loop, and an MP4
ambient video). Bearer-token auth uses `hmac.compare_digest` against a
TOML token file loaded from `~/.config/sask/tokens.toml`. Serialization
is entirely in `translators.py` — `app.py` has no `json.dumps` calls.

All runtime configuration (`SASK_HOST`, `SASK_PORT`, `SASK_TOKENS_PATH`,
`SASK_MANIFEST_PATH`) is via environment variables with sensible defaults,
exported automatically by `nix develop`. `scripts/run-local.sh` and
`scripts/run-tests.sh` added. 21 unit tests pass; full smoke test verified
with curl against all four resources. Results logged in `tests/results/PR-002.md`.

Also added `ruff` to the Nix dev shell (Poetry-installed ruff doesn't run on
NixOS). Workflow note: going forward, each PR gets a results file in
`tests/results/` capturing verbose pytest output and smoke test evidence.

Reference: PR-002, ADR-0002, REQ-FUN-001, REQ-FUN-002.

## 2026-05-10 — PR-001 done

All acceptance criteria verified. Added missing `.gitignore` (Python, Poetry,
Nix, OpenTofu, Ansible, SQLite, editor/OS patterns, secrets safety net) and
`docs/notes/.gitkeep`. Squashed two scaffolding commits into one.
Status set to done.

## 2026-05-10 — PR-001 scaffolding

Initialized the project. Established the spec-driven workflow with TOML
ADRs, requirements, and PR specs. Decided against GitHub Actions and
remote CI; everything runs locally. Local NixOS dev environment via
flake; deploy target is an Ubuntu droplet on Digital Ocean. Added shell prompt marker so I can tell whether I'm in the project shell. 

Reference: PR-001, ADR-0001.
