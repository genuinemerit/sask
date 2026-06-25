#!/usr/bin/env bash
# Regenerate requirements.txt from poetry.lock's "main" group — Poetry 2.x
# has no built-in `export` (the export plugin isn't in the Nix shell), so
# this reads the lock file directly via tomllib instead. poetry.lock's
# per-package `groups` already reflects the full resolved set (including
# transitive deps), so it alone is sufficient — pyproject.toml's own
# dependency list only has the direct ones.
#
#   bash tools/ops/export-requirements.sh

set -euo pipefail

cd "$(dirname "$0")/../.."

python3 - <<'PYEOF'
import tomllib
from pathlib import Path

lock = tomllib.loads(Path("poetry.lock").read_text())

lines = [
    f"{pkg['name']}=={pkg['version']}"
    for pkg in lock["package"]
    if "main" in pkg.get("groups", [])
]
lines.sort(key=str.lower)

Path("requirements.txt").write_text("\n".join(lines) + "\n")
print(f"Wrote {len(lines)} pinned requirements to requirements.txt")
PYEOF
