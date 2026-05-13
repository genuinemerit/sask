#!/usr/bin/env bash
# Export main Poetry dependencies to requirements.txt for production deployment.
# Excludes dev and acceptance groups; no hashes (faster pip install on droplet).
#
# Uses a Python script to read poetry.lock directly — this avoids a dependency
# on the poetry-plugin-export plugin, which is a separate install in Poetry 2.x.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 - <<'PYEOF'
import tomllib, sys

with open("poetry.lock", "rb") as f:
    lock = tomllib.load(f)

with open("pyproject.toml", "rb") as f:
    proj = tomllib.load(f)

groups = proj.get("tool", {}).get("poetry", {}).get("group", {})
exclude = set()
for gname in ("dev", "acceptance"):
    exclude |= set(groups.get(gname, {}).get("dependencies", {}).keys())
exclude_lower = {p.lower() for p in exclude}

lines = []
for pkg in lock["package"]:
    name = pkg["name"]
    version = pkg["version"]
    if "main" not in pkg.get("groups", ["main"]):
        continue
    if name.lower() in exclude_lower:
        continue
    markers = pkg.get("markers")
    marker = markers.get("main") if isinstance(markers, dict) else markers
    lines.append(f"{name}=={version} ; {marker}" if marker else f"{name}=={version}")

lines.sort()
with open("requirements.txt", "w") as f:
    f.write("\n".join(lines) + "\n")

print(f"Exported {len(lines)} packages to requirements.txt")
PYEOF
