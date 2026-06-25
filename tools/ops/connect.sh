#!/usr/bin/env bash
# SSH to the sask droplet via its alias — the only place an IP is ever
# referenced (REQ-OPS-014).
#
#   bash tools/ops/connect.sh                      # interactive shell
#   bash tools/ops/connect.sh 'systemctl status sask'   # one-off command

set -euo pipefail

exec ssh sask-droplet "$@"
