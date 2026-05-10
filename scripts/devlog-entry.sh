#!/usr/bin/env bash
# Open the dev log in $EDITOR with today's date prefilled at the top.
set -euo pipefail
cd "$(dirname "$0")/.."
LOG="docs/devlog.md"
TODAY="$(date -I)"
# Prepend a new dated header if today's date isn't already the most recent entry.
if ! head -n 5 "$LOG" | grep -q "^## $TODAY"; then
  TMP="$(mktemp)"
  {
    head -n 1 "$LOG"           # title line
    echo
    echo "## $TODAY — "
    echo
    tail -n +2 "$LOG"
  } > "$TMP"
  mv "$TMP" "$LOG"
fi
"${EDITOR:-vi}" "$LOG"

