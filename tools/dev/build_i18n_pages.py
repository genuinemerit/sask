"""Dev-side page builder: tagged base sources -> rendered per-locale help
pages (DD-0023, SPEC-036).

Reads docs/help_src/*.md (tagged BASE sources, dev-only, never served) and
the shared i18n catalog (config/i18n/*.toml, via sask.config_loader), and
generates:

  - en-US: resolves {tag} placeholders to en-US spellings and writes
    directly to docs/help/{topic}.md (the served base page). Deterministic
    -- pure tag resolution, no translation, safe to run unattended.
  - es-ES: resolves {tag} placeholders to es-ES spellings first (so
    invented proper nouns are already correct), then writes an
    INTERMEDIATE DRAFT to docs/help_src/.drafts/{topic}.es-ES.md -- never
    directly to docs/help/. The surrounding English prose in the draft
    still needs translating by a human (or an author-time LLM pass) with
    an explicit instruction to preserve the already-substituted proper
    nouns verbatim; only after that review does the result get promoted to
    docs/help/{topic}.es-ES.md and committed. This is the reviewable-draft
    boundary DD-0023 requires -- the builder never ships es-ES content
    unseen.

This script runs ONLY in dev, imports the sask package directly (poetry
run), and is never invoked by deploy.sh (see DD-0023's dev_prod_split) --
unlike tools/dev/validate_i18n.py, it has no bare-python3 constraint since
nothing in the pre-commit/deploy chain calls it.

Usage:
    poetry run python3 tools/dev/build_i18n_pages.py
    poetry run python3 tools/dev/build_i18n_pages.py --topic getting-started
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from sask.config_loader import I18nCatalog, load_config  # noqa: E402
from sask.i18n.catalog import resolve  # noqa: E402

BASE_SRC_DIR = ROOT / "docs" / "help_src"
SERVED_DIR = ROOT / "docs" / "help"
DRAFT_DIR = BASE_SRC_DIR / ".drafts"

_TAG_TOKEN_RE = re.compile(r"\{([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+)\}")


def render_page(base_text: str, locale: str, i18n: I18nCatalog) -> str:
    """Resolve every {tag} token in base_text against the catalog for locale.

    Pure function (no I/O) so the pre-commit staleness check and tests can
    both exercise it directly against a base source's text.
    """

    def _sub(match: re.Match[str]) -> str:
        return resolve(match.group(1), locale, i18n)

    return _TAG_TOKEN_RE.sub(_sub, base_text)


def _build_one(base_path: Path, i18n: I18nCatalog) -> None:
    topic = base_path.stem
    base_text = base_path.read_text(encoding="utf-8")

    en_text = render_page(base_text, "en-US", i18n)
    served_en = SERVED_DIR / f"{topic}.md"
    served_en.write_text(en_text, encoding="utf-8")
    print(f"[en-US] wrote {served_en.relative_to(ROOT)} (deterministic)")

    es_terms_substituted = render_page(base_text, "es-ES", i18n)
    DRAFT_DIR.mkdir(parents=True, exist_ok=True)
    draft_path = DRAFT_DIR / f"{topic}.es-ES.md"
    draft_path.write_text(es_terms_substituted, encoding="utf-8")
    print(
        f"[es-ES] wrote DRAFT {draft_path.relative_to(ROOT)} "
        "(proper nouns substituted; surrounding prose still needs "
        "translation + human review before promoting to "
        f"docs/help/{topic}.es-ES.md)"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--topic",
        help="Build only this topic (base filename stem); default: all base sources.",
    )
    args = parser.parse_args()

    config = load_config(ROOT / "config")

    if not BASE_SRC_DIR.is_dir():
        print(
            f"ERROR: base source directory not found: {BASE_SRC_DIR}", file=sys.stderr
        )
        return 1

    base_paths = sorted(BASE_SRC_DIR.glob("*.md"))
    if args.topic:
        base_paths = [p for p in base_paths if p.stem == args.topic]
        if not base_paths:
            print(f"ERROR: no base source for topic {args.topic!r}", file=sys.stderr)
            return 1

    if not base_paths:
        print(f"ERROR: no base sources found in {BASE_SRC_DIR}", file=sys.stderr)
        return 1

    for base_path in base_paths:
        _build_one(base_path, config.i18n)

    return 0


if __name__ == "__main__":
    sys.exit(main())
