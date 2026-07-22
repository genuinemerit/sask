"""`sask acceptance-test` (DD-0021, DD-0025, REQ-FUN-017, SPEC-038).

Admin-tier: thin subprocess wrap of tools/ops/acceptance-test.sh — the
Layer 2 (SPEC-024) curl smoke test against a live HTTPS endpoint. No
reimplementation; the script's own logic is invoked unchanged. tools/ is not
deployed to the droplet (ansible/roles/app/tasks/main.yml only syncs
src/sask/, config/, assets, docs/help/, wsgi.py), so this command is
functional wherever a full repo checkout exists (dev, or an operator's
machine) and reports a clean error if tools/ops/acceptance-test.sh is
missing — see _subprocess.run_tool's own docstring for why this needs an
explicit existence check rather than relying on subprocess.run to raise.
"""

from __future__ import annotations

import os

import typer

from .._paths import repo_root
from .._subprocess import run_tool


def acceptance_test(
    base_url: str | None = typer.Option(
        None,
        "--base-url",
        help="Override the tested base URL (script default: "
        "https://sask.davidstitt.net)",
    ),
) -> None:
    """Run the Layer 2 acceptance suite against a live sask endpoint.

    Example usage:
    `sask acceptance-test`
    `sask acceptance-test --base-url https://staging.example`
    """
    env = dict(os.environ)
    if base_url:
        env["SASK_BASE_URL"] = base_url
    run_tool(["bash"], repo_root() / "tools" / "ops" / "acceptance-test.sh", env=env)
