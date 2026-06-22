# Testing strategy — the four layers, mapped onto `sask-calendar`

`sask`'s `docs/notes/lessons.md` §6 ("Testing methodology: a frank
reckoning") lays out a four-layer testing discipline applied specifically to
the deploy lifecycle, not just the application. It's worth preserving the
layering exactly — each layer catches a class of defect the layer below it
structurally cannot.

## Layer 1 — Unit tests (already established in `sask-calendar`)

`sask` used Flask's test client against the application in isolation — no
network, no real secrets file, no real manifest on disk. `sask-calendar`
already has the equivalent and more: `tests/test_spec_NNN.py` per engine
SPEC, run via `tools/run-tests.sh`. **Nothing to port here.** The only
addition the deploy work makes to this layer is procedural: the existing
unit suite must pass *before* any deploy attempt, the same way `sask`
required `scripts/validate-specs.sh` to exit 0 as PR-003/PR-004's first
acceptance item.

## Layer 2 — Bash smoke test against the live endpoint

`sask/scripts/acceptance-test.sh`: curl-based, fast, human-readable,
`pass`/`fail` helpers, exits non-zero on first failure. Structurally this
ports as-is. Its *content* doesn't — it asserts on bearer-token auth and
resource byte-identity, neither of which necessarily applies to
`sask-calendar`'s web UI (see `open-questions.md` on whether the UI needs
auth at all). A `sask-calendar` equivalent would assert at minimum:

- The deployed root page (or `/health`, if one gets added) returns 200.
- TLS is valid (no `-k` needed).
- A real rendered page contains expected content (e.g. a known label or
  computed value for a fixed test input), the deployed-pipeline analogue of
  `sask`'s byte-identity check — proof the whole chain (DNS → TLS → Caddy →
  gunicorn → Flask → engine → template) produced a real result, not just
  proof the process is listening.

## Layer 3 — Pytest acceptance suite against the real HTTPS endpoint

`sask/tests/acceptance/{conftest.py,test_remote.py}`. Uses `requests`
against the actual deployed service — not Flask's test client — specifically
because some defects are only visible through the full stack: a Caddyfile
misconfiguration, an environment variable that didn't make it into the
systemd unit's `EnvironmentFile`, a TLS chain issue. A unit test cannot
catch any of those; an acceptance test run against the live droplet can and,
per `sask`'s own record, did surface several of the pitfalls logged in
`deployment-architecture.md`.

Directly portable from `conftest.py`:

```python
@pytest.fixture(scope="session")
def base_url() -> str:
    return _BASE_URL   # the deployed domain, https://
```

The `token`/`auth_headers` fixtures are conditional on whether the port adds
any form of access control — drop them if not, keep the pattern if so.

Directly portable from `test_remote.py` (structure, not assertions):
`test_health_returns_200`, `test_tls_certificate_is_valid`. The
resource-kind-specific tests (image/json/audio content type, byte-identity
against a local asset) don't apply unless `sask-calendar` ends up serving
comparable downloadable assets — but the **byte-identity pattern itself**
(hash a known local file, hash what the live endpoint returns, assert
equal) is the right template if `sask-calendar`'s ephemeris download
endpoints (`SPEC-018`/`SPEC-020`/`SPEC-021` territory) ever get an
acceptance test against the deployed droplet.

Location convention to carry over: `tests/acceptance/`, separate from the
main `tests/` unit suite, with its own `conftest.py` reading whatever local
secrets file applies and exposing fixtures by name rather than hardcoding
values into test bodies.

## Layer 4 — Operational acceptance tests (manual, scripted, recorded)

Some properties of a deployed system can't be expressed as a pytest
assertion; they require a deliberate exercise, with the outcome recorded as
evidence rather than just observed. `sask` ran three, all of which apply
unchanged to the port:

1. **Kill/restart test.** Kill the application process (`pkill`/`kill -9`)
   on the live droplet; confirm systemd restarts it within the configured
   `RestartSec` window and the service responds correctly immediately after.
   `sask`'s measured recovery: 6 seconds (`RestartSec=5s` + ~1s boot).
2. **Idempotency test.** Run the deploy script twice consecutively against
   an already-converged droplet. The acceptance bar is `changed=0` on the
   *second* run across every Ansible task — not just "no errors."
3. **Destroy → reprovision → redeploy from zero.** Tear down all cloud
   resources, provision fresh, deploy, and run the full Layer 2 + Layer 3
   suites against the new instance. This is the test that actually proves
   the "redeploy" and "idempotent deploy" claims in the task brief — a
   script that merely *runs* without erroring is not the same claim as a
   script that, run from zero, reproduces a working, verified service.

## Evidence recording convention

`sask-calendar` already has the right shape for this via REQ-OPS-005 and the
`tests/results/SPEC-NNN.md` convention (see `tests/results/SPEC-001.md`
through `SPEC-009.md` for the existing pattern, and
`tests/results/perf/` for evidence that this directory already holds more
than just unit-test logs). Port `sask`'s `tests/results/PR-003.md` /
`PR-004.md` structure directly onto the equivalent future
`tests/results/SPEC-0XX.md`:

- An acceptance checklist table (item, status: PASS/PENDING).
- Static checks section (lint, syntax-check, deliverables-present).
- A live-run section per real apply/deploy, with resource counts and timing.
- An explicit idempotency section showing two consecutive runs'
  `ok=N changed=0` output.
- An explicit destroy+reprovision+redeploy section with before/after IPs
  (proving the reserved-IP design held) and the full re-run of Layers 2–3
  against the fresh instance.

Raw command output that's too long for the markdown table belongs in
sibling files the way `sask` did it: `tests/results/SPEC-0XX-provision.txt`,
`tests/results/SPEC-0XX-destroy.txt`, referenced from the main results
file rather than inlined.

## What this methodology is actually buying

Worth carrying the framing forward, not just the mechanics, into whatever
SPEC eventually documents this: a test that was performed but not recorded
can't be audited or repeated, and a deploy script that "seems to work" is
not the same claim as one with a recorded `changed=0` second run and a
recorded full destroy/reprovision/redeploy cycle. The acceptance criteria in
`sask`'s PR-003/PR-004 specs were written *before* implementation began,
specifically so "how will I know this is true, with evidence I can show
someone else" had an answer in advance rather than a retrofit.
