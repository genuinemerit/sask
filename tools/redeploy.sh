#!/usr/bin/env bash
# The single mainline act (REQ-OPS-013): recreate the droplet -> deploy ->
# verify, in one invocation. Uses tools/recreate-droplet.sh, not the
# combination of destroy.sh + provision.sh — that pair tears down
# everything including the reserved IP itself, which would break the
# "DNS and the SSH alias survive unchanged" guarantee this script exists
# to demonstrate.
#
#   bash tools/redeploy.sh        # interactive: prompts at each tofu step
#   bash tools/redeploy.sh -y     # non-interactive throughout

set -euo pipefail

cd "$(dirname "$0")/.."

FLAG="${1:-}"

bash tools/recreate-droplet.sh "$FLAG"
bash tools/deploy.sh
bash tools/acceptance-test.sh
