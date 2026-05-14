# sask — Project conventions for Claude Code

This file is read automatically by Claude Code when launched in this directory.
It describes how this project is structured and how to work within it.

## What this project is

`sask` is a small experimental resource server: a remote service running on a
Digital Ocean droplet, delivering authenticated images / JSON / audio to a
local game client. It is a hobby project with strong emphasis on
**dev project as code** — provisioning, deployment, teardown, and
configuration are all version-controlled and scripted.

## Structure

- `src/sask/` — Python package (Flask application).
  - `app.py` — Application factory (`create_app()`); `/health` and `/resource/<kind>/<id>` routes.
  - `auth.py` — Bearer-token loading and validation (`hmac.compare_digest`).
  - `manifest.py` — Resource manifest loading (`ResourceEntry` dataclass, `load_manifest()`).
  - `translators.py` — All JSON serialization and file reading for HTTP responses.
- `resources/` — Placeholder resource files served by the application.
  - `manifest.toml` — Maps `(kind, id)` pairs to file paths and MIME types.
  - `images/`, `json/`, `audio/` — Asset sub-directories.
- `tests/` — pytest test suite (`conftest.py`, `test_health.py`, `test_auth.py`, `test_resources.py`).
- `decisions/` — Architecture Decision Records as TOML. Schema in `_schema.toml`.
- `requirements/` — Functional and operational requirements as TOML. Schema in `_schema.toml`.
- `prs/` — PR specifications: structured work units that drive implementation. Schema in `_schema.toml`.
- `infra/` — OpenTofu infrastructure-as-code for the DO droplet.
  - `versions.tf` — Provider version pins (`digitalocean ~> 2.0`, `http ~> 3.4`, `local ~> 2.5`).
  - `variables.tf` — All tunable inputs (region, size, image, SSH key paths).
  - `main.tf` — Droplet, reserved IP, reserved IP assignment, cloud firewall (SSH from developer IP only; HTTP/HTTPS from anywhere).
  - `ssh-config.tf` — `local_file` resource writing `~/.ssh/config.d/sask` (permissions 0600).
  - `outputs.tf` — `reserved_ip`, `droplet_id`, and `next_steps` (DNS instructions).
  - `terraform.tfvars.example` — Commented-out defaults; copy to `terraform.tfvars` to override.
  - `.gitignore` — Excludes state files, lock file, and tfvars.
- `ansible/` — Ansible playbook for service deployment to the droplet.
  - `ansible.cfg` — Disables host key checking; points SSH at `~/.ssh/config.d/sask`.
  - `inventory.yml` — Single host `sask-droplet` (resolved via SSH config alias).
  - `site.yml` — Top-level playbook: runs `base`, `sask_service`, `caddy` roles in order.
  - `group_vars/all.yml` — All tunable variables (paths, domain, gunicorn workers, `apt_upgrade`).
  - `roles/base/` — apt update, base packages, `sask` system user, `/opt/sask /etc/sask /var/log/sask` dirs.
  - `roles/sask_service/` — venv + pip install, copy source + resources, tokens deploy, systemd unit + env file.
  - `roles/caddy/` — Caddy apt repo + install, Caddyfile template (HTTPS reverse proxy, auto Let's Encrypt).
- `scripts/` — Bash orchestration scripts. Idempotent where possible.
- `tools/` — Python helpers (validators, generators).
- `docs/devlog.md` — Dev log. Mainly human-written. Read for context; do not write to it without explicit instruction.
- `docs/references.md` — Curated links and references.
- `docs/notes/` — Free-form notes.
- `secrets/` — Secrets directory. Contents gitignored except `*.example` files and `README.md`.

## Conventions

### Spec-driven work
- Each unit of implementation work is described by a TOML file in `prs/`.
- Before implementing, read the linked ADRs and requirements.
- After implementing, produce evidence against the `acceptance` checklist.
- Do not silently expand `scope.in` — surface scope questions explicitly.

### Code style
- Python 3.12.
- Poetry for dependency management.
- Explicit translator functions for serialization, not Pydantic or auto-serializers.
- pytest for tests.

- Small, focused modules. Prefer functions to classes unless state is genuine.

### Secrets
- Never commit secrets. Never hardcode tokens.
- Real secrets live outside the repo (`~/.config/sask/`) or are deployed via Ansible.
- Examples and templates use the `.example` suffix.

### Scripts
- Bash for orchestration, Python for logic.
- Each script: small, single-purpose, idempotent if possible, exits non-zero on failure.
- Reference scripts in PR specs rather than embedding commands inline.

### Git
- Remote: https://github.com/genuinemerit/sask (SSH: `git@github.com:genuinemerit/sask.git`)
- Linear commits to `main` unless experimenting on a branch.
- One commit per PR-spec implementation, message references the PR id (e.g. `PR-002: hex math`).
- Housekeeping commits are permitted for small fixes, status updates, and devlog entries (e.g. `PR-002: mark complete, update devlog`).

## Running the service

```bash
# Install dependencies (required once after clone or dependency changes)
poetry install

# Start the local dev server (binds to 127.0.0.1:8080 by default)
scripts/run-local.sh

# Run the test suite
scripts/run-tests.sh
```

## Deploying the service

Requires a provisioned droplet (run `scripts/provision.sh` first) and
`~/.config/sask/tokens.toml` with at least one valid token entry.

```bash
# Deploy: exports requirements, copies code/secrets, configures gunicorn + Caddy
scripts/deploy.sh          # prompts for confirmation (currently non-interactive; -y accepted)
scripts/deploy.sh -y

# Quick bash smoke test against the live HTTPS endpoint
scripts/acceptance-test.sh

# Full pytest acceptance suite against the live endpoint
poetry run pytest tests/acceptance/ -v

# Re-export requirements.txt after any dependency changes
scripts/export-requirements.sh
```

## Provisioning the droplet

Requires `~/.config/sask/infra.env` exporting `DIGITALOCEAN_TOKEN` (see `secrets/README.md`).

```bash
# Provision droplet, reserved IP, firewall, and SSH config snippet
scripts/provision.sh          # prompts for confirmation
scripts/provision.sh -y       # non-interactive

# SSH into the droplet (uses ~/.ssh/config.d/sask generated by tofu apply)
scripts/connect.sh

# Tear down all cloud resources
scripts/destroy.sh            # prompts for confirmation
scripts/destroy.sh -y         # non-interactive
```

DNS is managed by Tofu (`digitalocean_record`). After `provision.sh` completes,
wait for propagation: `dig +short sask.davidstitt.net` until it returns the reserved IP.

Runtime is configured via environment variables set automatically by `nix develop`:

| Variable | Default | Purpose |
|---|---|---|
| `SASK_HOST` | `127.0.0.1` | Bind address |
| `SASK_PORT` | `8080` | Bind port |
| `SASK_TOKENS_PATH` | `~/.config/sask/tokens.toml` | Authorized tokens file |
| `SASK_MANIFEST_PATH` | `$PROJECT_ROOT/resources/manifest.toml` | Resource manifest |

## Tools available in dev shell

After `nix develop`: `python` (3.12), `poetry`, `ruff`, `tofu`, `ansible`, `ssh`, `sqlite`, `jq`, `curl`.

## What to do on first launch in this repo

1. Read this file.
2. Read `prs/` to understand the current task, if any.
3. Read `decisions/` and `requirements/` to understand established constraints.
4. Read `docs/devlog.md` for recent context.
