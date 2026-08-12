#!/usr/bin/env bash
# Fast diagnosis for "ssh sask-droplet" hanging/timing out: checks whether
# it's the known cause — the DO Cloud Firewall's SSH rule pinned to a stale
# developer IP (REQ-OPS-014) — before you go digging further.
#
# Reads the local tofu state directly, so no DIGITALOCEAN_TOKEN needed.
#
#   bash tools/ops/check-ip-drift.sh

set -euo pipefail

cd "$(dirname "$0")/../.."

STATE_FILE="infra/tofu/terraform.tfstate"
if [[ ! -f "$STATE_FILE" ]]; then
    printf '[FAIL] %s not found — run from a dev host with tofu state present.\n' "$STATE_FILE" >&2
    exit 2
fi

ALLOWED_IP=$(jq -r '
    .resources[]
    | select(.type == "digitalocean_firewall" and .name == "sask")
    | .instances[0].attributes.inbound_rule[]
    | select(.port_range == "22")
    | .source_addresses[0] // empty
' "$STATE_FILE")
ALLOWED_IP="${ALLOWED_IP%%/*}"

if [[ -z "$ALLOWED_IP" ]]; then
    printf '[FAIL] Could not find the port-22 inbound rule in %s.\n' "$STATE_FILE" >&2
    exit 2
fi

CURRENT_IP=$(curl -s --max-time 5 https://api.ipify.org || true)
if [[ -z "$CURRENT_IP" ]]; then
    printf '[WARN] Could not reach api.ipify.org to determine your current IP.\n' >&2
    exit 2
fi

if [[ "$ALLOWED_IP" == "$CURRENT_IP" ]]; then
    printf '[OK] Firewall SSH rule already allows your current IP (%s).\n' "$CURRENT_IP"
    printf '     If ssh sask-droplet still times out, look elsewhere (droplet\n'
    printf '     down, sshd stopped, etc.) — the DO web console is the fallback.\n'
    exit 0
fi

printf '[DRIFT] Firewall SSH rule is stale — this is almost certainly why ssh sask-droplet times out.\n' >&2
printf '        Firewall currently allows: %s\n' "$ALLOWED_IP" >&2
printf '        Your current public IP is: %s\n' "$CURRENT_IP" >&2
printf '\n' >&2
printf '        Fix: bash tools/ops/provision.sh\n' >&2
exit 1
