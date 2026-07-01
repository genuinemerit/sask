"""Pytest suite for tools/helpers/validate_json.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "helpers"))
import validate_json  # noqa: E402

SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["name"],
    "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
}


def write(tmp_path: Path, name: str, obj: object) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(obj), encoding="utf-8")
    return path


# ── Happy path ──────────────────────────────────────────────────────────────


def test_valid_data_exits_zero_with_no_output(tmp_path, capsys, monkeypatch):
    schema_path = write(tmp_path, "schema.json", SCHEMA)
    data_path = write(tmp_path, "data.json", {"name": "sask", "age": 1})
    monkeypatch.setattr(
        sys, "argv", ["validate_json.py", str(schema_path), str(data_path)]
    )

    assert validate_json.main() == 0
    assert capsys.readouterr().out == ""


# ── Unhappy path ────────────────────────────────────────────────────────────


def test_schema_violation_exits_nonzero_and_reports_path(tmp_path, capsys, monkeypatch):
    schema_path = write(tmp_path, "schema.json", SCHEMA)
    data_path = write(tmp_path, "data.json", {"age": "not-an-int"})
    monkeypatch.setattr(
        sys, "argv", ["validate_json.py", str(schema_path), str(data_path)]
    )

    assert validate_json.main() == 1
    out = capsys.readouterr().out
    assert "name" in out  # missing required field reported
    assert "age" in out  # wrong type reported


def test_missing_data_file_exits_two_with_friendly_message(
    tmp_path, capsys, monkeypatch
):
    schema_path = write(tmp_path, "schema.json", SCHEMA)
    missing_path = tmp_path / "does-not-exist.json"
    monkeypatch.setattr(
        sys, "argv", ["validate_json.py", str(schema_path), str(missing_path)]
    )

    assert validate_json.main() == 2
    err = capsys.readouterr().err
    assert "file not found" in err
    assert "Traceback" not in err


def test_malformed_json_exits_two_with_friendly_message(tmp_path, capsys, monkeypatch):
    schema_path = write(tmp_path, "schema.json", SCHEMA)
    data_path = tmp_path / "data.json"
    data_path.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setattr(
        sys, "argv", ["validate_json.py", str(schema_path), str(data_path)]
    )

    assert validate_json.main() == 2
    err = capsys.readouterr().err
    assert "Traceback" not in err
