#!/usr/bin/env bash
# SSH to the sask droplet via its alias — the only place an IP is ever
# referenced (REQ-OPS-014).
#
#   bash tools/ops/connect.sh                      # interactive shell
#   bash tools/ops/connect.sh 'systemctl status sask'   # one-off command
#
# If this hangs and times out, it's usually the DO Cloud Firewall's SSH rule
# pinned to a stale developer IP (REQ-OPS-014) — see the hint printed below.

set -uo pipefail

if ! ssh sask-droplet "$@"; then
    status=$?
    printf '\n[connect.sh] ssh exited %d. If it timed out, diagnose with:\n' "$status" >&2
    printf '[connect.sh]     bash tools/ops/check-ip-drift.sh\n' >&2
    exit "$status"
fi
