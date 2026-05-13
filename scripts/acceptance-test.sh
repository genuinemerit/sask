#!/usr/bin/env bash
# Quick smoke test: hit the deployed service and verify all endpoints work.
# Exits 0 on success, 1 on any failure.
set -euo pipefail
cd "$(dirname "$0")/.."

DOMAIN="sask.davidstitt.net"
TOKENS_FILE="$HOME/.config/sask/tokens.toml"

if [[ ! -f "$TOKENS_FILE" ]]; then
  echo "Error: $TOKENS_FILE not found." >&2
  exit 1
fi

# Extract first token from local file
TOKEN=$(awk -F'"' '/^token = / {print $2; exit}' "$TOKENS_FILE")

if [[ -z "$TOKEN" ]]; then
  echo "Error: could not extract token from $TOKENS_FILE." >&2
  exit 1
fi

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

pass() {
  echo "PASS: $1"
}

# Test 1: health (no auth)
status=$(curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN/health")
[[ "$status" == "200" ]] || fail "health endpoint returned $status"
pass "health endpoint returns 200"

# Test 2: resource without token
status=$(curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN/resource/json/scenario-001")
[[ "$status" == "401" ]] || fail "missing-token returned $status (expected 401)"
pass "missing-token returns 401"

# Test 3: resource with bad token
status=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer not-a-real-token" "https://$DOMAIN/resource/json/scenario-001")
[[ "$status" == "401" ]] || fail "bad-token returned $status (expected 401)"
pass "bad-token returns 401"

# Test 4: unknown id
status=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "https://$DOMAIN/resource/json/no-such-id")
[[ "$status" == "404" ]] || fail "unknown-id returned $status (expected 404)"
pass "unknown-id returns 404"

# Test 5: valid retrieval for each kind
for path in "image/splash" "json/scenario-001" "audio/ambient-loop" "audio/ambient-video"; do
  status=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "https://$DOMAIN/resource/$path")
  [[ "$status" == "200" ]] || fail "GET $path returned $status (expected 200)"
  pass "GET $path returns 200"
done

# Test 6: byte-identity (one resource)
curl -s -H "Authorization: Bearer $TOKEN" "https://$DOMAIN/resource/image/splash" -o /tmp/sask-remote-splash.png
local_hash=$(sha256sum resources/images/splash.png | cut -d' ' -f1)
remote_hash=$(sha256sum /tmp/sask-remote-splash.png | cut -d' ' -f1)
[[ "$local_hash" == "$remote_hash" ]] || fail "splash.png bytes differ between local and remote"
pass "splash.png byte-identical between local and remote"
rm -f /tmp/sask-remote-splash.png

echo
echo "All smoke tests passed."
