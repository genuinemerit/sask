"""Validate a JSON data file against a JSON Schema (Draft 2020-12).

Usage:
    python tools/candidates/validate_json.py SCHEMA.json DATA.json

Prints one line per validation error (JSON path: message) and exits
non-zero if any are found; exits 0 with no output on success.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a JSON data file against a JSON Schema (Draft 2020-12)."
    )
    parser.add_argument("schema_path", type=Path, help="Path to the JSON Schema file.")
    parser.add_argument("data_path", type=Path, help="Path to the JSON data file.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    schema = json.loads(args.schema_path.read_text())
    data = json.loads(args.data_path.read_text())

    errors = sorted(
        Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path)
    )
    for error in errors:
        print(f"{list(error.path)}: {error.message}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
