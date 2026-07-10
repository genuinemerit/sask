"""Validate i18n catalogs (config/i18n/*.toml) — DD-0022, REQ-OPS-021, SPEC-035.

Three checks, self-contained (no sask package import — mirrors
validate_specs.py's convention, since this runs via bare `python3`, not
`poetry run`, in pre-commit-check.sh):

  1. Malformed tag (violates dotted-lowercase naming) — hard error, always.
  2. Missing base content (a tag present in a non-base locale but absent
     from en-US, the completeness floor) — hard error, always.
  3. Missing non-base translation (a tag present in en-US but absent from
     a declared non-base locale) — WARNING in permissive mode (default),
     hard error with --strict (the deploy gate).

Exit codes:
  0 — clean (permissive: no malformed/missing-base; strict: also no
      missing-non-base)
  1 — one or more hard errors for the active mode
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
I18N_DIR = ROOT / "config" / "i18n"
BASE_LOCALE = "en-US"

_TAG_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


def _load_toml(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def _load_catalog(i18n_dir: Path) -> dict[str, dict[str, str]]:
    """Return {locale: {tag: text}} for every config/i18n/*.toml file."""
    entries: dict[str, dict[str, str]] = {}
    for path in sorted(i18n_dir.glob("*.toml")):
        raw = _load_toml(path)
        entries[path.stem] = dict(raw.get("tags", {}))
    return entries


def run(i18n_dir: Path, strict: bool) -> list[str]:
    """Validate the catalog; return a list of "ERROR: ..."/"WARNING: ..." strings."""
    messages: list[str] = []

    if not i18n_dir.is_dir():
        return [f"ERROR: i18n catalog directory not found: {i18n_dir}"]

    catalog = _load_catalog(i18n_dir)

    if BASE_LOCALE not in catalog:
        return [
            f"ERROR: base locale file not found: {i18n_dir / f'{BASE_LOCALE}.toml'}"
        ]

    # Check 1: malformed tags, every locale, always a hard error.
    for locale, tags in catalog.items():
        for tag in tags:
            if not _TAG_RE.match(tag):
                messages.append(f"ERROR: {locale}.toml: malformed tag {tag!r}")

    base_tags = set(catalog[BASE_LOCALE])

    # Check 2: a tag present in a non-base locale but absent from base --
    # the base is the completeness floor; missing it is always a hard error.
    for locale, tags in catalog.items():
        if locale == BASE_LOCALE:
            continue
        orphans = set(tags) - base_tags
        for tag in sorted(orphans):
            messages.append(
                f"ERROR: {BASE_LOCALE}.toml: missing content for tag {tag!r} "
                f"(present in {locale}.toml)"
            )

    # Check 3: a tag present in base but absent from a non-base locale --
    # warn in permissive mode, hard error in strict mode (the deploy gate).
    level = "ERROR" if strict else "WARNING"
    for locale, tags in catalog.items():
        if locale == BASE_LOCALE:
            continue
        missing = base_tags - set(tags)
        for tag in sorted(missing):
            messages.append(
                f"{level}: {locale}.toml: missing translation for tag {tag!r}"
            )

    return messages


def main() -> int:
    strict = "--strict" in sys.argv[1:]
    messages = run(I18N_DIR, strict)

    for message in messages:
        stream = sys.stderr if message.startswith("ERROR") else sys.stdout
        print(message, file=stream)

    if any(m.startswith("ERROR") for m in messages):
        return 1

    mode = "strict" if strict else "permissive"
    if messages:
        print(f"i18n catalog valid ({mode} mode, warnings above).")
    else:
        print(f"i18n catalog valid ({mode} mode).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
