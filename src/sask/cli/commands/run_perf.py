"""`sask run_perf` (DD-0021, DD-0025, REQ-FUN-017, SPEC-038).

Admin-tier: thin subprocess wrap of tools/ops/run_perf.sh — the SPEC-018
Layer 1 engine benchmarks. No reimplementation; see acceptance_test.py's
docstring for the tools/-not-deployed-to-prod note, which applies here too.
"""

from __future__ import annotations

from .._paths import repo_root
from .._subprocess import run_tool


def run_perf() -> None:
    """Run the Layer 1 engine benchmarks and save a baseline.

    Example usage:
    `sask run_perf`
    """
    run_tool(["bash", str(repo_root() / "tools" / "ops" / "run_perf.sh")])
