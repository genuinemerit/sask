# sask — Development log

Reverse-chronological. Newest entries at top. Hand-written or auto-generated.

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
