#!/usr/bin/env bash
# Destroy sask infrastructure. Sources infra.env, runs tofu destroy.
# Default: prompts before destroying. Use -y to skip prompt.
set -euo pipefail
cd "$(dirname "$0")/.."

INFRA_ENV="$HOME/.config/sask/infra.env"
AUTO=""

if [[ "${1:-}" == "-y" ]]; then
  AUTO="-auto-approve"
fi

if [[ ! -f "$INFRA_ENV" ]]; then
  echo "Error: $INFRA_ENV not found." >&2
  exit 1
fi

set -a
source "$INFRA_ENV"
set +a

cd infra
tofu destroy $AUTO

