"""Dev-tier commands (DD-0021, DD-0025, REQ-FUN-017, SPEC-038).

Development/build/verification tooling that only makes sense in a
development environment — gated by SASK_ENV (cli/_env.py), not auth. Each
command is a thin subprocess wrap of its existing tools/dev/ script; no
logic is reimplemented, no behavior changes. Registration (hidden=not
is_dev_env()) happens once in cli/__init__.py; each command body also calls
require_dev() itself as defense in depth.

Each _TOOLS_DEV / "..." script path is passed to _subprocess.run_tool,
which checks the path's existence itself before invoking (see its own
docstring for why that check can't be left to subprocess.run/except
FileNotFoundError).
"""

from __future__ import annotations

import sys

import typer

from .._env import require_dev
from .._paths import repo_root
from .._subprocess import run_tool

_TOOLS_DEV = repo_root() / "tools" / "dev"


def check_page_staleness() -> None:
    """Guard that committed rendered help pages stay current (DD-0023).

    Example usage:
    `sask check_page_staleness`
    """
    require_dev()
    run_tool([sys.executable], _TOOLS_DEV / "check_page_staleness.py")


def pre_commit_check() -> None:
    """Run every pre-commit check (ruff, shellcheck, pymarkdown, design docs, i18n).

    Example usage:
    `sask pre-commit-check`
    """
    require_dev()
    run_tool(["bash"], _TOOLS_DEV / "pre-commit-check.sh")


def run_tests(
    spec: str | None = typer.Option(
        None, "--spec", help="Run only the tests for one spec (e.g. SPEC-002)"
    ),
    verbose: bool = typer.Option(
        False, "-v", "--verbose", help="Verbose pytest output"
    ),
    save: bool = typer.Option(
        False,
        "--save",
        help="Save results to tests/results/<SPEC-ID>.md (requires --spec)",
    ),
) -> None:
    """Run the unit test suite (configurable scope/verbosity/saving).

    Example usage:
    `sask run-tests --spec SPEC-002 -v --save`
    """
    require_dev()
    args = []
    if spec:
        args += ["--spec", spec]
    if verbose:
        args.append("-v")
    if save:
        args.append("--save")
    run_tool(["bash"], _TOOLS_DEV / "run-tests.sh", args=args)


def start_web() -> None:
    """Start the sask Flask development server (foreground).

    Example usage:
    `sask start_web`
    """
    require_dev()
    run_tool(["bash"], _TOOLS_DEV / "start_web.sh")


def verify_clean_env() -> None:
    """Verify a clean-environment dev-host setup (SPEC-031).

    Example usage:
    `sask verify-clean-env`
    """
    require_dev()
    run_tool(["bash"], _TOOLS_DEV / "verify-clean-env.sh")


def verify_do_secrets() -> None:
    """Verify DigitalOcean host secrets are present/valid (REQ-SEC-006: never prints values).

    Example usage:
    `sask verify-do-secrets`
    """
    require_dev()
    run_tool(["bash"], _TOOLS_DEV / "verify-do-secrets.sh")


def validate_specs() -> None:
    """Validate design/ dd, req, and spec TOML files against their schemas.

    Example usage:
    `sask validate_specs`
    """
    require_dev()
    run_tool([sys.executable], _TOOLS_DEV / "validate_specs.py")


def validate_i18n(
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Hard-fail on missing non-base translations too (the deploy-time gate)",
    ),
) -> None:
    """Validate i18n catalogs (config/i18n/*.toml).

    Example usage:
    `sask validate_i18n --strict`
    """
    require_dev()
    args = ["--strict"] if strict else []
    run_tool([sys.executable], _TOOLS_DEV / "validate_i18n.py", args=args)
