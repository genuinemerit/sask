# secrets/

This directory documents the secrets convention but contains no secrets.

## Categories

### Infrastructure secrets
DO API token, SSH private key.
**Location:** `~/.config/sask/infra.env` (outside the repo).
**Sourced by:** deploy and destroy scripts via `set -a; source ~/.config/sask/infra.env; set +a`.

### Application secrets
Authorized client tokens for the resource service.
**Local template:** `secrets/tokens.toml.example` (this directory).
**Real file:** `~/.config/sask/tokens.toml` (outside the repo).
**Deployed by:** Ansible (PR-004), to `/etc/sask/tokens.toml` on the droplet.

## Gitignore

Everything in this directory is gitignored except this README and `*.example` files.
