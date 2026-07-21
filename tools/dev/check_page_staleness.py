"""Pre-commit staleness check for DD-0023 page-builder rendered pages (SPEC-036).

Guards that committed rendered help pages stay current with their tagged
base sources (docs/help_src/*.md), per DD-0023's page-is-code principle:

  - en-US: DETERMINISTIC. Re-renders each base source and compares
    byte-for-byte against the committed docs/help/{topic}.md. Any
    difference is a hard error -- en-US rendering is pure tag resolution,
    so "stale" always means "forgot to re-run the builder," never "needs
    judgment."
  - es-ES: HUMAN-FLAG. Translation can't be auto-regenerated, so instead
    of re-rendering, this compares the base source's current content hash
    against the hash recorded in docs/help_src/translation-status.toml at
    the time the committed es-ES translation was last reviewed. A
    mismatch (or missing entry) is a hard error: "base changed since the
    es-ES translation was reviewed -- re-translate and update the
    manifest to acknowledge." Updating the manifest IS the human
    acknowledgment DD-0023 requires; this check never auto-updates it.

Unlike validate_specs.py/validate_i18n.py, this script imports the sask
package directly (poetry run) rather than reimplementing tag resolution,
to avoid two divergent copies of resolve()'s fallback semantics.

Usage:
    poetry run python3 tools/dev/check_page_staleness.py
    poetry run python3 tools/dev/check_page_staleness.py --acknowledge getting-started
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sask.config_loader import load_config  # noqa: E402

import build_i18n_pages  # noqa: E402

BASE_SRC_DIR = ROOT / "docs" / "help_src"
SERVED_DIR = ROOT / "docs" / "help"
MANIFEST_PATH = BASE_SRC_DIR / "translation-status.toml"


def _display(path: Path) -> str:
    """Path relative to ROOT for display, or the raw path if outside ROOT
    (e.g. a test fixture under a tmp_path)."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _base_hash(base_text: str) -> str:
    return "sha256:" + hashlib.sha256(base_text.encode("utf-8")).hexdigest()


def _load_manifest() -> dict[str, dict[str, str]]:
    if not MANIFEST_PATH.is_file():
        return {}
    with MANIFEST_PATH.open("rb") as f:
        return tomllib.load(f)


def _write_manifest(manifest: dict[str, dict[str, str]]) -> None:
    lines = [
        "# Tracks which base-source content hash each committed es-ES",
        "# translation was last reviewed against (DD-0023 page-is-code",
        "# staleness check, SPEC-036). Updated ONLY by a human running",
        "# `check_page_staleness.py --acknowledge <topic>` after reviewing",
        "# a fresh/updated translation -- never auto-updated by the builder.",
        "",
    ]
    for topic in sorted(manifest):
        lines.append(f"[{topic}]")
        for locale in sorted(manifest[topic]):
            lines.append(f'{locale} = "{manifest[topic][locale]}"')
        lines.append("")
    MANIFEST_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def check() -> list[str]:
    """Return a list of "ERROR: ..." strings; empty means clean."""
    errors: list[str] = []

    if not BASE_SRC_DIR.is_dir():
        return errors  # nothing to check yet

    config = load_config(ROOT / "config")
    manifest = _load_manifest()

    for base_path in sorted(BASE_SRC_DIR.glob("*.md")):
        topic = base_path.stem
        base_text = base_path.read_text(encoding="utf-8")

        # en-US: deterministic -- must match a fresh regeneration exactly.
        served_en = SERVED_DIR / f"{topic}.md"
        expected_en = build_i18n_pages.render_page(base_text, "en-US", config.i18n)
        if not served_en.is_file():
            errors.append(
                f"ERROR: {_display(served_en)} does not exist -- "
                f"run: poetry run python3 tools/dev/build_i18n_pages.py --topic {topic}"
            )
        elif served_en.read_text(encoding="utf-8") != expected_en:
            errors.append(
                f"ERROR: {_display(served_en)} is stale relative to "
                f"{_display(base_path)} -- re-run: poetry run python3 "
                f"tools/dev/build_i18n_pages.py --topic {topic}"
            )

        # es-ES: human-flag -- base hash must match the last-reviewed hash
        # recorded in the manifest for a committed translation to exist.
        served_es = SERVED_DIR / f"{topic}.es-ES.md"
        if not served_es.is_file():
            continue  # no es-ES translation yet -- nothing to go stale
        current_hash = _base_hash(base_text)
        recorded_hash = manifest.get(topic, {}).get("es-ES")
        if recorded_hash != current_hash:
            errors.append(
                f"ERROR: {_display(base_path)} changed since "
                f"{_display(served_es)} was last reviewed -- "
                "re-translate and review it, then acknowledge with: "
                f"poetry run python3 tools/dev/check_page_staleness.py "
                f"--acknowledge {topic}"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--acknowledge",
        metavar="TOPIC",
        help="Record the current base-source hash as reviewed for TOPIC's "
        "es-ES translation (the human acknowledgment DD-0023 requires -- "
        "run this only after actually reviewing the translation).",
    )
    args = parser.parse_args()

    if args.acknowledge:
        base_path = BASE_SRC_DIR / f"{args.acknowledge}.md"
        if not base_path.is_file():
            print(
                f"ERROR: no base source for topic {args.acknowledge!r}", file=sys.stderr
            )
            return 1
        manifest = _load_manifest()
        manifest.setdefault(args.acknowledge, {})["es-ES"] = _base_hash(
            base_path.read_text(encoding="utf-8")
        )
        _write_manifest(manifest)
        print(f"Acknowledged {args.acknowledge!r}'s es-ES translation as current.")
        return 0

    errors = check()
    for message in errors:
        print(message, file=sys.stderr)

    if errors:
        return 1

    print("Page staleness check: all rendered pages current.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
