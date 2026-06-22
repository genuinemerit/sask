# Test results: SPEC-024

**Spec:** SPEC-024 — Deployment acceptance and operational test suite
**Date:** 2026-06-22
**Status:** PASS — every acceptance item verified, including the full
destroy/reprovision/redeploy cycle deferred from SPEC-022 and SPEC-023.

---

## Layer 1 — unit suite gate

```text
$ .venv/bin/pytest tests/ -q
608 passed in 1.69s
```

Confirmed before any deploy action, per REQ-OPS-010's existing convention.

## Layer 2 — tools/acceptance-test.sh

```text
$ bash tools/acceptance-test.sh
[PASS]  TLS validates without -k
[PASS]  /health returns 200
[PASS]  root page contains the expected computed value (104548096103)

[ALL PASS] Acceptance suite complete.
```

## Layer 3 — pytest acceptance suite (tests/acceptance/)

```text
$ .venv/bin/pytest tests/acceptance/ -v
tests/acceptance/test_remote.py::test_health_returns_200 PASSED
tests/acceptance/test_remote.py::test_tls_certificate_is_valid PASSED
tests/acceptance/test_remote.py::test_root_page_renders_expected_value PASSED
3 passed in 0.56s
```

Uses `requests` against the live domain, not Flask's test client. Added a
new `acceptance` Poetry dependency group for `requests` (anticipated by
the original design's "filtering dev/acceptance groups" language, but not
previously created) — confirmed it's correctly excluded from
`requirements.txt` (only the `main` group is exported; the droplet has no
need for a testing-only HTTP client). `tests/acceptance/` is excluded from
the default `pytest`/`pytest tests/` run via `norecursedirs`
(`pyproject.toml`) — confirmed default run still collects exactly 608,
not 611.

## Layer 4 — operational tests

### Kill/restart (re-confirmed from SPEC-023, same mechanism)

```text
$ sudo pkill -9 -f gunicorn
$ systemctl status sask
Active: active (running) since ...; ~2s ago    # fresh PID
$ curl -s -o /dev/null -w "%{http_code}" https://sask.davidstitt.net/health
200
```

### Idempotency

Two consecutive `tools/deploy.sh` runs, no manual steps between them, both
`changed=0` (established in SPEC-023's evidence; re-confirmed again here
immediately after the full redeploy cycle below).

### Full destroy -> reprovision -> redeploy cycle

**First attempt surfaced a real design gap, not a glitch.** Running
`tools/redeploy.sh -y` (at the time: `destroy.sh` + `provision.sh` +
`deploy.sh`) completed with `failed=0` throughout — but the **reserved IP
itself changed** (`129.212.194.54` -> `104.248.101.239`), contradicting
REQ-OPS-013's explicit guarantee ("the public DNS name and SSH alias
resolve unchanged **(reserved IP held)**"). Root cause: `destroy.sh`'s
second `tofu destroy` call has no `-target`, so it tears down every
resource in state, including `digitalocean_reserved_ip.sask` — the right
behavior for a genuine full teardown (which `destroy.sh` still is, run
standalone), but not for a redeploy meant to preserve network identity.
The site itself kept working throughout (DNS correctly updated to the new
IP, TLS/health all fine) — this was a guarantee violation, not an outage.

Presented to the developer as a real design choice, not silently
patched. Decided: add `tools/recreate-droplet.sh`, which destroys/recreates
*only* the droplet resource (reserved IP, DNS record, firewall, SSH key all
stay in Tofu state); `tools/redeploy.sh` now calls it instead of
`destroy.sh` + `provision.sh`, and also gained the verify step
(`tools/acceptance-test.sh`) that wasn't available when SPEC-023 first
wrote it.

Re-ran the corrected cycle for real:

```text
Before: droplet_id = "579514354"  reserved_ip = "104.248.101.239"

$ tools/redeploy.sh -y
Plan: 3 to add, 0 to change, 0 to destroy.   # droplet + dependent firewall +
                                              # reassignment only - Tofu cascades
                                              # dependents of a targeted destroy
Changes to Outputs:
  ~ droplet_id  = "579514354" -> (known after apply)
                                              # reserved_ip absent from this list - unchanged
Apply complete! Resources: 3 added, 0 changed, 0 destroyed.

After:  droplet_id = "579520422"  reserved_ip = "104.248.101.239"   # IDENTICAL

PLAY RECAP: sask-droplet : ok=35  changed=29  unreachable=0  failed=0  skipped=1
[PASS]  TLS validates without -k
[PASS]  /health returns 200
[PASS]  root page contains the expected computed value (104548096103)
[ALL PASS] Acceptance suite complete.

$ python3 -c "import socket; print(socket.gethostbyname('sask.davidstitt.net'))"
104.248.101.239   # DNS still resolves correctly, same IP throughout
```

`droplet_id` changed; `reserved_ip` did not. The single `redeploy.sh -y`
invocation now genuinely performs recreate -> deploy -> verify as one
act, with `failed=0` and the verify step passing automatically. A
follow-up idempotency check (`tools/deploy.sh` run again, no changes in
between) confirmed `changed=0` on the fresh droplet too.

---

## Acceptance criteria

| Item | Status |
| --- | --- |
| Layer 2 passes against the live endpoint and exits non-zero on first failure | PASS |
| Layer 3 pytest acceptance passes against the real domain | PASS |
| Layer 4: restart recovery measured | PASS |
| Layer 4: deploy `changed=0` second run captured | PASS |
| Layer 4: full destroy/reprovision/redeploy cycle, Layers 2-3 green, before/after IPs noted | PASS |
| Evidence written to tests/results/ in the current convention | PASS |
| Unit suite confirmed green before any deploy (Layer 1 gate) | PASS |

---

## Deviations and notes

- `tools/recreate-droplet.sh` was added during this spec's own testing,
  not anticipated by SPEC-022/023's original drafts — see both specs'
  updated scope sections. `tools/destroy.sh` is intentionally left
  unchanged (full teardown remains the right tool when the goal is
  paying nothing); only `redeploy.sh` was repointed at the narrower
  script.
- `tools/redeploy.sh` previously had no verify step (acceptance-test.sh
  didn't exist when SPEC-023 wrote it) — now wired in, so the single
  mainline `redeploy.sh -y` command genuinely satisfies REQ-OPS-013's
  "destroy -> provision -> deploy -> verify as one act" end to end.
- This is the second time in this deploy effort that a real run (not
  linting) surfaced a gap between the documented design intent and the
  literal implementation — same pattern as SPEC-023's three runtime bugs.
  Worth keeping the practice of actually executing destructive/lifecycle
  operations for real rather than trusting a clean dry-run alone.
