#!/usr/bin/env bash
# Snapshot the repo layout (excluding VCS/build/cache noise) to tree.txt at
# the repo root — useful for quick structure reviews or pasting into docs.
set -euo pipefail

cd "$(dirname "$0")/../.." || exit 1

tree -a -I '.git|.mypy_cache|.pytest_cache|__pycache__|.venv|.direnv|dist|build' -L 4 > tree.txt
echo "Wrote $(pwd)/tree.txt"
