#!/usr/bin/env bash
# Deploy sask to the provisioned droplet.
# Idempotent: run as often as you like.
# Prerequisites:
#   - Droplet provisioned (scripts/provision.sh)
#   - ~/.config/sask/tokens.toml exists locally
#   - ~/.config/sask/infra.env exists locally
set -euo pipefail
cd "$(dirname "$0")/.."

INFRA_ENV="$HOME/.config/sask/infra.env"
TOKENS_FILE="$HOME/.config/sask/tokens.toml"
AUTO=""

if [[ "${1:-}" == "-y" ]]; then
  AUTO="--extra-vars assume_yes=true"
fi

# Preflight checks
if [[ ! -f "$INFRA_ENV" ]]; then
  echo "Error: $INFRA_ENV not found. See secrets/README.md." >&2
  exit 1
fi

if [[ ! -f "$TOKENS_FILE" ]]; then
  echo "Error: $TOKENS_FILE not found." >&2
  echo "Create it with at least one token entry. See secrets/tokens.toml.example." >&2
  exit 1
fi

# Refresh requirements.txt
scripts/export-requirements.sh

# Source DO token (not needed for Ansible, but harmless and consistent with other scripts)
set -a
source "$INFRA_ENV"
set +a

# Run the playbook
cd ansible
ansible-playbook site.yml
