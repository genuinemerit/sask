"""Enables `python -m sask.cli` (DD-0021, SPEC-034).

The pyproject.toml console script (`sask = "sask.cli:main"`) only exists
where the sask package itself is pip/poetry-installed with entry points —
true in dev (poetry install), but NOT on the droplet, where the app role
installs only requirements.txt's dependencies and runs the app via
PYTHONPATH (see ansible/roles/app/tasks/*.yml), the same way wsgi.py does.
`python -m sask.cli` works via plain module import, matching that same
PYTHONPATH-based invocation, so the CLI is runnable on the droplet without
changing the deploy/install model.
"""

from sask.cli import main

if __name__ == "__main__":
    main()
