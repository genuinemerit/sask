"""`sask validate_json SCHEMA DATA` (DD-0021, DD-0025, REQ-FUN-017, SPEC-038).

Player-tier: generic, read-only JSON-Schema (Draft 2020-12) validation
utility. Self-contained — mirrors tools/helpers/validate_json.py's logic
exactly (that script stays untouched for its own callers/tests), rather than
importing it: tools/ is not part of the deployed package
(ansible/roles/app/tasks/main.yml only syncs src/sask/), so a player-tier
command meant to work in prod carries its own copy of the same logic.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from jsonschema import Draft202012Validator

from ..formatting import echo_error


def validate_json(
    schema_path: Path = typer.Argument(..., help="Path to the JSON Schema file"),
    data_path: Path = typer.Argument(..., help="Path to the JSON data file"),
) -> None:
    """Validate a JSON data file against a JSON Schema (Draft 2020-12).

    Prints one line per validation error (JSON path: message); exits
    non-zero if any are found, 0 with no output on success.

    Example usage:
    `sask validate_json schema.json data.json`
    """
    try:
        schema = json.loads(schema_path.read_text())
        data = json.loads(data_path.read_text())
    except FileNotFoundError as exc:
        echo_error(f"{exc.filename}: file not found")
        raise typer.Exit(2) from None
    except json.JSONDecodeError as exc:
        echo_error(str(exc))
        raise typer.Exit(2) from None

    errors = sorted(
        Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path)
    )
    for error in errors:
        typer.echo(f"{list(error.path)}: {error.message}")

    if errors:
        raise typer.Exit(1)
