#!/usr/bin/env bash
# Pre-commit checks — run from any directory; stops at first failure.
# Every check must exit 0 before staging a commit.

set -uo pipefail

cd "$(dirname "$0")/../.." || exit 1

run_check() {
    local label="$1"
    shift
    printf '\n[CHECK] %s\n' "$label"
    if ! "$@"; then
        printf '\n[FAIL]  %s — fix the issues above, then re-run.\n' "$label" >&2
        exit 1
    fi
    printf '[PASS]  %s\n' "$label"
}

run_check "ruff lint" \
    poetry run ruff check tools/ tests/ src/

run_check "ruff format" \
    poetry run ruff format --check tools/ tests/ src/

# -S warning: tools/ops/perf-remote.sh deliberately expands a few $REMOTE_*
# variables client-side inside double-quoted ssh command strings (SC2029,
# info-level) — that's the intended behavior, not a bug, so info-level
# notes are excluded rather than disabled line-by-line.
run_check "shellcheck" \
    shellcheck -S warning tools/*/*.sh

run_check "pymarkdown" \
    poetry run pymarkdown --config .pymarkdown scan \
        README.md CLAUDE.md docs/ tests/results/ secrets/README.md

run_check "validate_specs" \
    python3 tools/dev/validate_specs.py

run_check "pytest (validate_specs suite)" \
    poetry run pytest tests/test_validate_specs.py -q

# Permissive mode: malformed tags / missing base content still hard-fail;
# missing non-base translations only warn here (DD-0022, REQ-OPS-021).
# Strict mode (--strict, hard-fails incomplete locales too) is the
# deploy-time gate, not a commit-time one — see tools/ops/deploy.sh.
run_check "validate_i18n" \
    python3 tools/dev/validate_i18n.py

printf '\n[ALL PASS] Pre-commit checks complete.\n'
