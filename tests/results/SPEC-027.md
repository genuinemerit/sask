# Test results: SPEC-027

**Spec:** SPEC-027 — Deployed asset sync and rate-limited delivery
**Date:** PENDING — scaffolded ahead of an actual redeploy; not yet run.
**Status:** PENDING. The code/config changes (Ansible sync task, group_vars,
Caddy rate-limit zone, acceptance tests) are implemented and unit-tested
locally; this file records the live-redeploy verification, which is a
separate, deliberate, human-triggered infrastructure action per the
project's "no auto-run infrastructure" rule — not run as part of the coding
pass that produced this scaffold.

---

## Layer 1 — unit suite gate

```text
$ .venv/bin/pytest tests/ -q
626 passed in 1.96s
```

Confirmed before any deploy action (includes SPEC-026's 18 new tests; no
regressions across the ~20 existing `load_config(REAL_CONFIG)` call sites).

## Layer 2 — tools/acceptance-test.sh

PENDING — run after a real redeploy:

```text
bash tools/acceptance-test.sh
```

Expect the existing three checks plus the new asset checks:
`[PASS]  https://sask.davidstitt.net/asset/image/splash.bg returns 200` and
`[PASS]  .../asset/image/splash.bg Content-Type is image/webp`.

## Layer 3 — pytest acceptance suite (tests/acceptance/)

PENDING — run after a real redeploy:

```text
.venv/bin/pytest tests/acceptance/ -v
```

Expect `test_asset_bytes_match_local` (sha256 of the live response body
matches `assets/v0/image/splash.default.1920x1080.6389524a.webp`) and
`test_unknown_asset_returns_404` alongside the existing SPEC-024 tests.

## Layer 4 — operational tests

PENDING — run after a real redeploy:

- **Idempotency**: a second consecutive `tools/deploy.sh` reports `changed=0`
  for the new "Ensure the assets/ parent directory exists" and "Sync the
  assets/{{ assets_version }}/ tree" tasks, alongside the existing tasks.
- **Parity/isolation**: `assets/local/` is confirmed absent on the droplet;
  `assets/v0/` (image/, audio/, json/, video/) is confirmed present at the
  path `ASSETS_DIR` resolves to.
- **Delete semantics**: removing or renaming a local asset and redeploying
  removes/renames it on the droplet (matching `config/`'s sync behavior).
- **Rate limit**: rapid requests to a known asset URL trip the new `zone
  asset` Caddy rate limit (429 after `rate_limit_asset_events` within
  `rate_limit_asset_window`), and normal access resumes after the window
  elapses — confirms the zone is distinct from both `zone interactive`
  (60/1m) and `zone download` (4/1m).

---

## Acceptance criteria

| Item | Status |
| --- | --- |
| A redeploy syncs assets/{{ assets_version }}/ under app_root; assets/local/ never appears on the droplet | PENDING |
| A second consecutive deploy reports changed=0 for the new sync task | PENDING |
| The new sync task notifies the same restart handler as the existing src/config tasks | PENDING |
| A live GET for a known (kind, id) returns 200, the catalog content_type, and matching sha256 bytes | PENDING |
| A live GET for an unknown (kind, id) returns the adapter's not-found response | PENDING |
| The asset Caddy rate-limit zone is active and distinct from both the default and ephemeris-download zones | PENDING |
| Removing or renaming a local asset and redeploying removes/renames it on the droplet | PENDING |
| tests/results/SPEC-027.md records all of the above | IN PROGRESS (this file) |

---

## Deviations and notes

- During implementation, the catalog's `kind` field was changed from
  authored to derived (computed from each asset's top-level subdirectory
  under `ASSETS_DIR`) — see DD-0016's amended `kind_is_config` section.
  This doesn't affect SPEC-027's deploy mechanics, only how
  `asset_catalog_data.toml` entries are shaped.
- `assets/<world>.manifest.json` remains `{}` and is not part of this
  spec's sync or load path — it's a deployed-state ledger tied to a
  not-yet-built publish pipeline, out of scope per DD-0016.
