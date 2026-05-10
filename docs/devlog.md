# sask — Development log

Reverse-chronological. Newest entries at top. Hand-written, not auto-generated.

## 2026-05-10 — PR-001 done

All acceptance criteria verified. Added missing `.gitignore` (Python, Poetry,
Nix, OpenTofu, Ansible, SQLite, editor/OS patterns, secrets safety net) and
`docs/notes/.gitkeep`. Squashed two scaffolding commits into one.
Status set to done.

## 2026-05-10 — PR-001 scaffolding

Initialized the project. Established the spec-driven workflow with TOML
ADRs, requirements, and PR specs. Decided against GitHub Actions and
remote CI; everything runs locally. Local NixOS dev environment via
flake; deploy target is an Ubuntu droplet on Digital Ocean. Added shell prompt marker so I can tell whether I'm in the project shell. 

Reference: PR-001, ADR-0001.
