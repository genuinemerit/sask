#!/usr/bin/env bash
# Change the droplet's SASK_LOG_LEVEL and restart the service (SPEC-032).
#
# Ansible-driven rather than a direct SSH edit: re-templates
# /etc/sask/environment from group_vars/all.yml's sask_log_level default,
# overridden for this run via -e, and restarts sask via the runtime role's
# handler chain. This keeps Ansible the single source of truth — a direct
# SSH+sed edit would be invisible to Ansible and get silently reverted back
# to the group_vars default on the next deploy.sh/redeploy.sh run.
#
# Stays a standalone ops script, not a CLI command (DD-0021, reaffirmed by
# DD-0025): service-mutating operations stay ops-side so Ansible remains the
# single source of truth.
#
#   bash tools/ops/set-log-level.sh DEBUG
#   bash tools/ops/set-log-level.sh INFO

set -euo pipefail

VALID_LEVELS=(CRITICAL ERROR WARNING INFO DEBUG TRACE)

LEVEL="${1:-}"
if [[ -z "$LEVEL" ]]; then
    printf '[FAIL] Usage: %s <LEVEL>\n' "$0" >&2
    printf '       LEVEL one of: %s\n' "${VALID_LEVELS[*]}" >&2
    exit 1
fi
LEVEL="${LEVEL^^}"

_valid=false
for candidate in "${VALID_LEVELS[@]}"; do
    if [[ "$LEVEL" == "$candidate" ]]; then
        _valid=true
        break
    fi
done
if [[ "$_valid" != true ]]; then
    printf '[FAIL] Unknown level %s. Must be one of: %s\n' "$LEVEL" "${VALID_LEVELS[*]}" >&2
    exit 1
fi

cd "$(dirname "$0")/../../ansible"

printf '[INFO] Setting SASK_LOG_LEVEL=%s on sask-droplet...\n' "$LEVEL"
ansible-playbook site.yml --tags runtime -e "sask_log_level=$LEVEL"
printf '[PASS] sask.service restarted at log level %s.\n' "$LEVEL"
