#!/usr/bin/env bash
# Start the sask resource server locally.
# Usage: scripts/run-local.sh
#
# Environment variables (all optional — sensible defaults apply):
#   SASK_HOST          Bind address         (default: 127.0.0.1)
#   SASK_PORT          Bind port            (default: 8080)
#   SASK_TOKENS_PATH   Path to tokens.toml  (default: ~/.config/sask/tokens.toml)
#   SASK_MANIFEST_PATH Path to manifest.toml (default: ./resources/manifest.toml)
set -euo pipefail

cd "$(dirname "$0")/.."

: "${SASK_HOST:=127.0.0.1}"
: "${SASK_PORT:=8080}"
: "${SASK_TOKENS_PATH:=${HOME}/.config/sask/tokens.toml}"
: "${SASK_MANIFEST_PATH:=$(pwd)/resources/manifest.toml}"

export SASK_HOST SASK_PORT SASK_TOKENS_PATH SASK_MANIFEST_PATH

echo "Starting sask on http://${SASK_HOST}:${SASK_PORT}"
echo "  tokens:   ${SASK_TOKENS_PATH}"
echo "  manifest: ${SASK_MANIFEST_PATH}"

exec poetry run flask --app src/sask/app:app run \
    --host "$SASK_HOST" \
    --port "$SASK_PORT"
