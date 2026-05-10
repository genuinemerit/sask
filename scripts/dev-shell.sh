#!/usr/bin/env bash
# Enter the project's pinned dev shell.
# Run this from anywhere; it cd's to the project root first.
set -euo pipefail
cd "$(dirname "$0")/.."
exec nix develop

