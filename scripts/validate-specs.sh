#!/usr/bin/env bash
# Validate all ADR, requirement, and PR-spec TOML files.
set -euo pipefail
cd "$(dirname "$0")/.."
python tools/validate_specs.py

