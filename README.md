# sask

A small experimental resource server delivering authenticated images, JSON, and audio
over HTTPS to a local game client. Hobby project exploring "dev project as code" on
NixOS + Digital Ocean — provisioning, deployment, teardown, and configuration are all
version-controlled and scripted.

## Status

Four PRs complete. Service live at `https://sask.davidstitt.net`.

| PR | Title | Key deliverables |
|----|-------|-----------------|
| PR-001 | Project scaffolding | Nix devshell, TOML spec schema, secrets policy (ADR-0001), validate-specs.sh |
| PR-002 | Local Flask service | Flask app, bearer-token auth, explicit translators, 21 unit tests |
| PR-003 | Droplet provisioning | OpenTofu infra (droplet, reserved IP, firewall, DNS), provision/destroy/connect scripts |
| PR-004 | Service deployment | Ansible (base/sask\_service/caddy roles), gunicorn + systemd, Caddy auto-TLS, 17 acceptance tests |

## Architecture decisions

Six ADRs recorded in `decisions/`:

- **ADR-0001** — Secrets never in repo; infra credentials via env vars, app tokens deployed by Ansible.
- **ADR-0002** — Flask + explicit translator functions in `translators.py`; no Pydantic or auto-serializers.
- **ADR-0003** — Local OpenTofu state (gitignored); migration path to DO Spaces documented if needed.
- **ADR-0004** — Single `s-1vcpu-1gb` droplet in fra1, reserved IP for stable DNS, DO cloud firewall.
- **ADR-0005** — Ansible roles + gunicorn (WSGI) + Caddy (reverse proxy, auto Let's Encrypt).
- **ADR-0006** — `tokens.toml` copied from developer machine by Ansible, mode 0600, never touches git.

## Running locally

```bash
# Install dependencies (once, or after dependency changes)
poetry install

# Start local dev server (127.0.0.1:8080)
scripts/run-local.sh

# Run unit tests
scripts/run-tests.sh
```

## Provisioning and deploying

Requires `~/.config/sask/infra.env` (exports `DIGITALOCEAN_TOKEN`) and
`~/.config/sask/tokens.toml` (at least one valid token entry).

```bash
# Provision droplet, reserved IP, firewall, SSH config, DNS record
scripts/provision.sh          # prompts for confirmation
scripts/provision.sh -y       # non-interactive

# Deploy service (exports requirements, syncs code, configures gunicorn + Caddy)
scripts/deploy.sh -y

# Bash smoke test against live HTTPS endpoint
scripts/acceptance-test.sh

# Full pytest acceptance suite against live endpoint
poetry run pytest tests/acceptance/ -v

# SSH into the droplet
scripts/connect.sh

# Tear down all cloud resources
scripts/destroy.sh -y
```

## Repository structure

```
src/sask/          Flask application (app.py, auth.py, manifest.py, translators.py)
resources/         Placeholder assets + manifest.toml
tests/             Unit tests (pytest)
tests/acceptance/  Acceptance tests against the live endpoint (pytest + requests)
tests/results/     Evidence files for each completed PR
infra/             OpenTofu configuration (.tf files, gitignored state)
ansible/           Playbook and roles for droplet configuration
scripts/           Bash orchestration scripts
decisions/         Architecture Decision Records (TOML)
requirements/      Functional and operational requirements (TOML)
prs/               PR specifications (TOML)
docs/              Devlog and references
secrets/           Gitignored secrets directory (.example files and README only)
```

## Dev environment

After `nix develop`: `python` (3.12), `poetry`, `ruff`, `tofu`, `ansible`, `ssh`, `sqlite`, `jq`, `curl`.

Runtime is configured via environment variables set automatically by `nix develop`:

| Variable | Default | Purpose |
|---|---|---|
| `SASK_HOST` | `127.0.0.1` | Bind address |
| `SASK_PORT` | `8080` | Bind port |
| `SASK_TOKENS_PATH` | `~/.config/sask/tokens.toml` | Authorized tokens file |
| `SASK_MANIFEST_PATH` | `$PROJECT_ROOT/resources/manifest.toml` | Resource manifest |
