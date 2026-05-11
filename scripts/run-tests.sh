#!/usr/bin/env bash
# Run the sask test suite.
# Usage: scripts/run-tests.sh
set -euo pipefail

cd "$(dirname "$0")/.."

poetry install --quiet
exec poetry run pytest tests/ -v
