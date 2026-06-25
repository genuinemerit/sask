#!/usr/bin/env bash
# The single mainline act (REQ-OPS-013): recreate the droplet -> deploy ->
# verify, in one invocation. Uses tools/ops/recreate-droplet.sh, not the
# combination of destroy.sh + provision.sh — that pair tears down
# everything including the reserved IP itself, which would break the
# "DNS and the SSH alias survive unchanged" guarantee this script exists
# to demonstrate.
#
#   bash tools/ops/redeploy.sh        # interactive: prompts at each tofu step
#   bash tools/ops/redeploy.sh -y     # non-interactive throughout

set -euo pipefail

cd "$(dirname "$0")/../.."

FLAG="${1:-}"

bash tools/ops/recreate-droplet.sh "$FLAG"
bash tools/ops/deploy.sh
bash tools/ops/acceptance-test.sh
