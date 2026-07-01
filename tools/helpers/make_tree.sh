#!/usr/bin/env bash
# Snapshot the repo layout (excluding VCS/build/cache noise) to tree.txt at
# the repo root — useful for quick structure reviews or pasting into docs.
set -euo pipefail

command -v tree >/dev/null || {
    echo "make_tree.sh: 'tree' is not installed (try: sudo apt-get install tree)" >&2
    exit 1
}

cd "$(dirname "$0")/../.."

tree -a -I '.git|.mypy_cache|.pytest_cache|__pycache__|.venv|.direnv|dist|build' -L 4 > tree.txt
echo "Wrote $(pwd)/tree.txt"
