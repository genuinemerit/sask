#!/usr/bin/env bash
# Export Poetry dependencies to requirements.txt for production deployment.
# Excludes dev dependencies; no hashes (faster pip install).
set -euo pipefail
cd "$(dirname "$0")/.."
poetry export -f requirements.txt --output requirements.txt --without-hashes --without dev,acceptance
echo "Exported $(wc -l < requirements.txt) packages to requirements.txt"
