#!/usr/bin/env bash
# SPEC-032 acceptance criterion 7 — automated live-log verification.
# Read-only: journalctl and cat over SSH, no mutation of droplet state.
#
#   bash tools/ops/verify-logging.sh
#   SASK_LOG_LINES=200 bash tools/ops/verify-logging.sh

set -euo pipefail

cd "$(dirname "$0")/../.."

LINES="${SASK_LOG_LINES:-50}"

pass() { printf '[PASS]  %s\n' "$1"; }
fail() {
    printf '[FAIL]  %s\n' "$1" >&2
    exit 1
}

# 1. At least some recent lines are well-formed app JSON, and no known
#    secret appears in cleartext anywhere in the window (REQ-SEC-004).
#    Not every line under the unit is expected to be JSON — gunicorn's own
#    startup/worker-boot notices are legitimate plain text (SPEC-032
#    deploy_wiring); only an absence of ANY well-formed app JSON line is a
#    failure. journalctl needs sudo to read the unit's journal (matches
#    the pattern already in docs/deploy-runbook.md); the actual privileged
#    read happens inside this remote Python process, not in the outer
#    ssh/python3 invocation.
REMOTE_CHECK=$(cat <<'PY'
import json
import subprocess
import sys

lines = subprocess.run(
    ["sudo", "journalctl", "-u", "sask", "-o", "cat", "-n", sys.argv[1], "--no-pager"],
    capture_output=True,
    text=True,
    check=True,
).stdout.splitlines()

required = ("timestamp", "level", "logger", "message")
needles = ("DIGITALOCEAN_TOKEN", "dop_v1_")

total = 0
json_ok = 0
secret_hits = 0

for raw in lines:
    line = raw.strip()
    if not line:
        continue
    total += 1
    for needle in needles:
        if needle in line and "REDACTED" not in line:
            secret_hits += 1
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        continue  # gunicorn's own plain-text startup/worker notices — expected
    if all(key in record for key in required):
        json_ok += 1

print(f"total={total} json_ok={json_ok} secret_hits={secret_hits}")
sys.exit(1 if (json_ok == 0 or secret_hits) else 0)
PY
)

echo "[CHECK] recent journal has well-formed app JSON and no cleartext secrets"
if result="$(bash tools/ops/connect.sh "python3 - $LINES" <<<"$REMOTE_CHECK")"; then
    pass "$result"
else
    fail "journal content check failed: ${result:-no output}"
fi

# 2. The journald size/retention drop-in is present with the values
#    group_vars/all.yml declares (deterministic — doesn't depend on how
#    much has actually accumulated yet).
echo "[CHECK] journald drop-in caps are applied"
DROPIN_CONTENT="$(bash tools/ops/connect.sh 'cat /etc/systemd/journald.conf.d/sask.conf' 2>/dev/null || true)"
if [[ -z "$DROPIN_CONTENT" ]]; then
    fail "/etc/systemd/journald.conf.d/sask.conf not found on sask-droplet"
fi
if ! grep -q '^SystemMaxUse=' <<<"$DROPIN_CONTENT"; then
    fail "SystemMaxUse not set in the journald drop-in"
fi
if ! grep -q '^MaxRetentionSec=' <<<"$DROPIN_CONTENT"; then
    fail "MaxRetentionSec not set in the journald drop-in"
fi
pass "journald drop-in present: $(tr '\n' ' ' <<<"$DROPIN_CONTENT")"

# 3. Informational only — current usage against the cap, for the human
#    reviewing this run; not a pass/fail (usage is naturally low/variable).
echo "[INFO] current journal disk usage:"
bash tools/ops/connect.sh 'journalctl --disk-usage' || true

printf '\n[ALL PASS] Log verification complete.\n'
