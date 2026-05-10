"""Validate ADR, requirement, and PR-spec TOML files against their schemas.

Exit codes:
  0 — all files valid
  1 — one or more files invalid
  2 — usage error
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = [
    (ROOT / "decisions",    "_schema.toml", "ADR"),
    (ROOT / "requirements", "_schema.toml", "Requirement"),
    (ROOT / "prs",          "_schema.toml", "PR spec"),
]


def load_toml(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def validate_dir(dir_path: Path, schema_name: str, label: str) -> list[str]:
    errors: list[str] = []
    schema_path = dir_path / schema_name
    if not schema_path.exists():
        errors.append(f"{label}: missing schema {schema_path}")
        return errors
    # Schema is loaded for future use; current validation is structural only.
    _ = load_toml(schema_path)
    for f in sorted(dir_path.glob("*.toml")):
        if f.name == schema_name:
            continue
        try:
            load_toml(f)
        except Exception as e:
            errors.append(f"{label}: {f.name} parse error: {e}")
    return errors


def main() -> int:
    all_errors: list[str] = []
    for dir_path, schema_name, label in TARGETS:
        if not dir_path.exists():
            all_errors.append(f"{label}: directory missing: {dir_path}")
            continue
        all_errors.extend(validate_dir(dir_path, schema_name, label))
    if all_errors:
        for e in all_errors:
            print(e, file=sys.stderr)
        return 1
    print("All spec files parsed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

