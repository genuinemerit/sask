# sask — Project conventions for Claude Code

This file is read automatically by Claude Code when launched in this directory.
It describes how this project is structured and how to work within it.

## What this project is

`sask` is a small experimental resource server: a remote service running on a
Digital Ocean droplet, delivering authenticated images / JSON / audio to a
local game client. It is a hobby project with strong emphasis on
**dev project as code** — provisioning, deployment, teardown, and
configuration are all version-controlled and scripted.

## Structure

- `decisions/` — Architecture Decision Records as TOML. Schema in `_schema.toml`.
- `requirements/` — Functional and operational requirements as TOML. Schema in `_schema.toml`.
- `prs/` — PR specifications: structured work units that drive implementation. Schema in `_schema.toml`.
- `scripts/` — Bash orchestration scripts. Idempotent where possible.
- `tools/` — Python helpers (validators, generators).
- `docs/devlog.md` — Human-written dev log. Read for context; do not write to it without explicit instruction.
- `docs/references.md` — Curated links and references.
- `docs/notes/` — Free-form notes.
- `secrets/` — Secrets directory. Contents gitignored except `*.example` files and `README.md`.

## Conventions

### Spec-driven work
- Each unit of implementation work is described by a TOML file in `prs/`.
- Before implementing, read the linked ADRs and requirements.
- After implementing, produce evidence against the `acceptance` checklist.
- Do not silently expand `scope.in` — surface scope questions explicitly.

### Code style
- Python 3.12.
- Poetry for dependency management.
- Explicit translator functions for serialization, not Pydantic or auto-serializers.
- pytest for tests.

- Small, focused modules. Prefer functions to classes unless state is genuine.

### Secrets
- Never commit secrets. Never hardcode tokens.
- Real secrets live outside the repo (`~/.config/sask/`) or are deployed via Ansible.
- Examples and templates use the `.example` suffix.

### Scripts
- Bash for orchestration, Python for logic.
- Each script: small, single-purpose, idempotent if possible, exits non-zero on failure.
- Reference scripts in PR specs rather than embedding commands inline.

### Git
- Local git only. No GitHub Actions, no branch protection.
- Linear commits to `main` unless experimenting on a branch.
- One commit per PR-spec implementation, message references the PR id (e.g. `PR-002: hex math`).

## Tools available in dev shell

After `nix develop`: `python` (3.12), `poetry`, `tofu`, `ansible`, `ssh`, `sqlite`, `jq`, `curl`.

## What to do on first launch in this repo

1. Read this file.
2. Read `prs/0001-scaffolding.toml` to understand the current task, if any.
3. Read `decisions/` and `requirements/` to understand established constraints.
4. Read `docs/devlog.md` for recent context.
