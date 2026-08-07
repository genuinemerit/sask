"""Pre-commit staleness check for the DD-0027/SPEC-040 API reference.

Guards that the committed docs/api_reference/{index.html,reference.json}
stay current with the code + config they're generated from, per DD-0023's
page-is-code principle, mirroring tools/dev/check_page_staleness.py's exact
two-tier split:

  - DETERMINISTIC tier: rebuilds the reference in-memory (calling
    build_api_reference.build_reference() directly, no file I/O beyond
    reading the prose source) and compares byte-for-byte against the
    committed artifacts. Any difference (a route/param/error-code changed,
    or the prose source was edited without rebuilding) is a hard error --
    the fix is always to re-run the builder and commit, never to hand-edit
    the artifact.
  - HUMAN-FLAG tier: build_reference() itself raises KeyError when a
    declared endpoint has no matching description in the prose source (a
    genuinely new endpoint) -- that specific failure is reported as the
    human-flag case (add a one-line description, then rebuild), distinct
    from an ordinary content mismatch.

Unlike validate_specs.py/validate_i18n.py, this script imports the sask
package and the builder directly (poetry run) rather than reimplementing
generation, to avoid two divergent copies of the build logic.

Usage:
    poetry run python3 tools/dev/check_api_reference_staleness.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sask.web import create_app  # noqa: E402

import build_api_reference  # noqa: E402

OUT_DIR = ROOT / "docs" / "api_reference"


def _display(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def check() -> list[str]:
    """Return a list of "ERROR: ..." strings; empty means clean."""
    html_path = OUT_DIR / "index.html"
    json_path = OUT_DIR / "reference.json"

    app = create_app(config_dir=ROOT / "config")
    try:
        expected_html, expected_json = build_api_reference.build_reference(app)
    except KeyError as exc:
        # Human-flag tier: a declared endpoint has no prose description.
        return [f"ERROR: {exc}"]

    errors: list[str] = []
    for path, expected, label in (
        (html_path, expected_html, "HTML"),
        (json_path, expected_json, "JSON"),
    ):
        if not path.is_file():
            errors.append(
                f"ERROR: {_display(path)} does not exist -- run: poetry run "
                "python3 tools/dev/build_api_reference.py"
            )
        elif path.read_text(encoding="utf-8") != expected:
            errors.append(
                f"ERROR: {_display(path)} ({label}) is stale relative to the "
                "code/config/prose source -- re-run: poetry run python3 "
                "tools/dev/build_api_reference.py"
            )
    return errors


def main() -> int:
    errors = check()
    for message in errors:
        print(message, file=sys.stderr)

    if errors:
        return 1

    print("API reference staleness check: artifacts current.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
