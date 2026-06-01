# Test results: SPEC-001

**Spec:** SPEC-001 — Scaffold sask repository and development environment
**Date:** 2026-06-01
**Status:** PASS — all host-side and VM smoke tests complete

---

## Host-side tests (Ubuntu host)

### pytest tests/test_validate_specs.py

```text
$ python3 -m pytest tests/test_validate_specs.py -v
14 passed in 0.12s
```

Status: PASS — 14 tests (spec anticipated 13; `test_corrupted_schema` added during
implementation, bringing the total to 14).

### python tools/validate_specs.py

```text
$ python3 tools/validate_specs.py
All spec files valid.
```

Status: PASS

### git check-ignore (REQ-SEC-002)

```text
$ git check-ignore -v secrets/some-secret.key
.gitignore:17:secrets/*    secrets/some-secret.key     ← ignored ✓

$ git check-ignore -v secrets/README.md
.gitignore:18:!secrets/README.md    secrets/README.md  ← negation, not ignored ✓
```

Status: PASS

---

## VM smoke tests

NixOS VM reconfigured per docs/vm-setup.md. devShell confirmed on 2026-06-01.

| Test | Status |
| --- | --- |
| `nix develop` succeeds on fresh clone | PASS |
| `python3 --version` matches flake.lock pin (3.12.13) | PASS |
| `poetry --version` matches flake.lock pin (2.2.1) | PASS |
| `ruff --version` runs inside devShell (0.14.6) | PASS |

---

## Acceptance criteria

| Item | Status |
| --- | --- |
| All linked requirements' acceptance criteria pass | PASS |
| First push lands on GitHub main with full tree and doc set | PASS |
| Applying configuration.nix on the VM + clean clone reproduces a working devShell | PASS |

---

## Deviations and notes

- `docs/vm-setup.md` added to deliverables (approved, outside original SPEC-001 scope).
- VM approach changed from fresh headless install to reconfiguring an existing NixOS 25.11
  KDE Plasma VM. `infra/configuration.nix` updated accordingly; spec and vm-setup.md revised.
- `flake.lock`, `poetry.lock`, and `requirements.txt` generated on VM and committed.
- `flake.nix` patched with `POETRY_VIRTUALENVS_PREFER_ACTIVE_PYTHON=true` and `LD_LIBRARY_PATH` fix for NixOS venv compatibility.
- `.venv` (pymarkdownlnt + pytest) created manually on VM; not committed (gitignored).
- `poetry export` replaced with `poetry run pip freeze` in vm-setup.md (export plugin unavailable).
- 14 pytest cases rather than the anticipated 13; `test_corrupted_schema` was added during
  implementation of the test suite.
- `tests/test_validate_specs.py::make_design_tree` helper fixed to create all three required
  subdirs with empty schemas, so happy-path tests see a complete valid design tree.
