#!/usr/bin/env bash
# The single mainline act (REQ-OPS-013): destroy -> provision -> deploy, in
# one invocation, preserving every ordering guard from the discrete scripts
# it calls (reserved-IP detach, re-provision on IP change, root-then-dave
# bootstrap). The verify step (SPEC-024's acceptance suite) is wired in
# once that spec lands.
#
#   bash tools/redeploy.sh        # interactive: prompts at each tofu step
#   bash tools/redeploy.sh -y     # non-interactive throughout

set -euo pipefail

cd "$(dirname "$0")/.."

FLAG="${1:-}"

bash tools/destroy.sh "$FLAG"
bash tools/provision.sh "$FLAG"
bash tools/deploy.sh
