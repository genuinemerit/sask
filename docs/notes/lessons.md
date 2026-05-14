# Lessons learned — sask baseline experiment

_Written after PR-004 completion. Covers the full baseline experiment:
scaffolding through live service deployment._

---

## 1. High-level summary

The sask experiment set out to answer one question: can a single developer
fully specify, implement, test, and operate a cloud-hosted service — including
provisioning, deployment, and teardown — without any manual steps beyond
running scripts? The answer, after four PRs, is yes.

The main points:

**Spec-driven development works well at this scale.** Writing TOML specs
(ADRs, requirements, PR specs) before touching code forced useful decisions
early and created a searchable record of why things are the way they are.
The validator script that ran against every spec file was a lightweight
but effective discipline tool.

**Infrastructure as code is not optional at hobby scale — it's a force
multiplier.** The destroy+reprovision cycle being a single command with no
manual DNS steps (because Tofu owns the DNS record), no SSH key uploads,
no firewall configuration — that's the payoff for the upfront work.

**Idempotency is the right goal.** Every script and playbook was designed
to converge to the desired state on repeated runs. This made debugging much
easier: when something went wrong, re-running the script would either fix it
or reproduce it cleanly.

**Secrets policy needs to be established first, not retrofitted.** ADR-0001
was written before any code or infrastructure. As a result, no token or key
ever appeared in a commit, a Tofu state file, or an Ansible log — even during
the messy debugging phase of PR-004.

**Tooling friction is real and should be fixed immediately.** The NixOS +
Poetry conflict (Poetry-installed binaries don't run under NixOS) was found
in PR-001 and fixed by adding `ruff` to the Nix dev shell. Carrying that
friction into later PRs would have been a constant irritant.

---

## 2. Key achievements

The goal was to build confidence and working knowledge across the full
stack of "dev project as code" — not just the application, but the entire
lifecycle around it. Measured against that goal:

**Full IaC lifecycle, no manual cloud steps.** OpenTofu manages every cloud
resource: droplet, reserved IP, firewall, SSH key, DNS record, and the local
SSH config snippet. `scripts/provision.sh` and `scripts/destroy.sh` are the
only interface. The destroy+reprovision cycle was validated end-to-end: old
IP released, new IP assigned, DNS updated automatically, fresh certificate
issued by Caddy — all without touching the DO web UI.

**Repeatable, idempotent deployment.** `scripts/deploy.sh` runs Ansible,
which converges the droplet to the desired state. Two consecutive runs after
initial deployment showed `changed=0` across all tasks. The same playbook
that deploys to a fresh droplet works as a day-two operations tool: re-run
it to push a code change or rotate tokens.

**Service reliability baseline.** The service runs as a systemd unit under
a non-root user (`sask`), with `Restart=on-failure`. The kill/restart test
showed a 6-second recovery time. Caddy auto-renews the Let's Encrypt
certificate with no manual intervention.

**End-to-end acceptance testing.** Two test suites validate the live
service: a bash smoke test (`scripts/acceptance-test.sh`) for quick manual
runs, and a pytest suite (`tests/acceptance/test_remote.py`, 17 tests) that
covers all happy and unhappy paths against the real HTTPS endpoint, including
byte-identity of retrieved resource files.

**Working secrets discipline.** Tokens never appear in git history, Tofu
state, or Ansible task output (`no_log: true` on the copy task). The
`deploy.sh` script exits with a clear error if the local tokens file is
missing. Verified with `git grep` and Tofu state inspection.

---

## 3. Per-PR implementation notes

### PR-001 — Project scaffolding

No significant technical obstacles. The main value was establishing
conventions that paid off in later PRs:

- The TOML schema files (`_schema.toml` in each directory) and the
  `validate-specs.sh` / `tools/validate_specs.py` pipeline created a low-cost
  consistency check that ran on every PR.
- Adding `ruff` to `flake.nix` immediately (rather than relying on
  `poetry run ruff`) avoided a recurring NixOS friction point.
- The secrets policy (ADR-0001) established before any credentials existed
  meant the `.gitignore` patterns were in place before they were needed.

### PR-002 — Local Flask service

**Issue: Flask app factory vs. module-level `app` object.**
The PR spec noted that `app.py` could use either pattern and that the choice
would affect the gunicorn ExecStart in PR-004. The factory pattern
(`create_app()`) was used; the consequence in PR-004 was that gunicorn
had to be invoked as `gunicorn 'sask.app:create_app()'` rather than
`gunicorn 'sask.app:app'`. Worth noting the coupling early.

**Design that held up: explicit translators.**
Keeping all serialization in `translators.py` (no `json.dumps` in `app.py`,
no Pydantic) paid dividends during PR-004 debugging. When something was wrong
with a response body, there was exactly one place to look.

**Design that held up: constant-time token comparison.**
`hmac.compare_digest` in `auth.py` is a one-line decision but the right one.
It's easy to get this wrong with a naive `==` comparison.

**Design that held up: env-var configuration.**
All four `SASK_*` variables with sensible defaults made the service
easy to run locally and easy to configure on the droplet via an Ansible-managed
environment file — no code changes between dev and prod.

### PR-003 — Droplet provisioning

**Issue: DigitalOcean renamed "floating IP" to "reserved IP" in 2022.**
The DO Terraform/Tofu provider version 2.x uses `digitalocean_reserved_ip`
and `digitalocean_reserved_ip_assignment`. Documentation and tutorials still
often reference the old names. If using a tutorial as a starting point,
expect to rename these resources.

**Issue: SSH firewall rule is tied to the developer's IP at apply time.**
The `http` data source fetches the current IP via ipify.org. If the
developer's IP changes (mobile, VPN, ISP rotation) between provision sessions,
re-running `scripts/provision.sh` updates the firewall rule and nothing else.
This is fast (~10s) but requires remembering to do it when connectivity changes.

**Decision that paid off: reserved IP strategy.**
The DNS A record points at the reserved IP, not the droplet. During the
destroy+reprovision cycle in PR-004, the droplet got a new ephemeral IP
(`129.212.169.212` reserved vs a different direct IP), but because Tofu
owns the DNS record and it points at the reserved IP, DNS propagation
happened automatically without any manual intervention.

**Decision that paid off: DNS management via Tofu.**
`digitalocean_record` in `main.tf` means DNS is part of the declarative
infrastructure. No GoDaddy manual step (an earlier devlog entry mentioned
a manual DNS step — this was replaced before PR-004 by moving the record
into Tofu). Destroy removes the record; provision creates it fresh.

**Trade-off accepted: local Tofu state.**
`infra/terraform.tfstate` lives on the developer's machine, gitignored.
This is the simplest setup and appropriate at hobby scale. The documented
risk: losing the state file means orphaned cloud resources requiring manual
cleanup. The migration path to DO Spaces remote state is recorded in
ADR-0003 for when/if that trade-off becomes unacceptable.

### PR-004 — Service deployment via Ansible

This PR had the most implementation friction and the most useful lessons.

**Issue: `~` not expanded in `ansible.cfg` subprocess SSH args.**
Setting `ssh_args = -F ~/.ssh/config.d/sask` in `ansible.cfg` does not
work — the `~` is not shell-expanded when Ansible invokes the SSH subprocess.
Fix: remove `-F` entirely and rely on the fact that `~/.ssh/config` contains
`Include ~/.ssh/config.d/*`. The sask-droplet alias resolves without an
explicit `-F`. This is simpler and works correctly.

**Issue: `ansible.builtin.pip` requires a remote path for `requirements:`.**
Ansible's pip module, when given a `requirements:` argument, expects the file
to already exist on the managed host — not on the controller. The fix:
copy `requirements.txt` to the droplet first (e.g., to `/tmp/`), then
reference the remote path in the pip task.

**Issue: `caddy validate` in a template `validate:` block runs as root.**
Caddy's config validation step (used to verify the Caddyfile before reloading)
creates log files as `root:root` when run as root during playbook execution.
Caddy itself runs as a system user and cannot write to its own log directory
afterward. Fix: remove the `validate:` block from the template; instead, add
a recursive `chown` task on `/var/log/caddy` after the Caddyfile is deployed.

**Issue: non-idempotent source file sync with `copy` module.**
Using `ansible.builtin.copy` for the `src/sask/` directory copied
`__pycache__` and applied the controller's local user ownership on every
run (rsync's `-o` flag). Fix: switch to `ansible.posix.synchronize`
(rsync wrapper) with `--exclude=__pycache__ --no-owner --no-group`.
This produces `changed=0` on repeated runs.

**Issue: `poetry export` not available in Poetry 2.x.**
Poetry 2.x moved `export` to a separate plugin (`poetry-plugin-export`)
that is not included in the Nix dev shell. Fix: `scripts/export-requirements.sh`
reads `poetry.lock` directly using a small Python script, rather than calling
`poetry export`. This is more brittle than the plugin but works without
additional Nix packaging.

**Design that held up: no Poetry in production.**
The venv on the droplet is populated with `pip install -r requirements.txt`.
Poetry is a dev tool; the production environment uses only pip and a
`requirements.txt` snapshot. This kept the deployment simple and avoided
any Poetry/Nix incompatibility on the droplet side.

**Design that held up: three-role structure.**
`base` / `sask_service` / `caddy` is the right granularity. Each role
has a single concern; handler scope is limited to the role that needs it
(Caddy reload in the caddy role, sask restart in sask_service). The
separation also makes it easy to re-run just one role during debugging.

---

## 4. Applying these lessons to a production gaming app

The sask experiment was deliberately minimal: one service, one droplet,
placeholder assets, a single developer. A full-sized gaming app with real
users, real assets, and real reliability requirements would extend these
patterns rather than replace them. Here's how each area maps:

### Infrastructure as code

The Tofu + reserved IP + DNS pattern scales directly. For a production
game with multiple services (auth, resource delivery, game state, etc.),
the natural extension is:

- Multiple droplets or a managed cluster, still provisioned declaratively.
- Remote Tofu state (DO Spaces or a managed backend) instead of local state.
  The migration path is documented in ADR-0003; for production, this is not
  optional — local state on a single machine is a single point of failure.
- Tofu workspaces or separate state files for staging and production
  environments.
- Reserved IPs (or a load balancer IP) per service endpoint, all managed
  in code.

### Secrets management

The two-category policy (infra credentials via env vars, app secrets via
Ansible) holds for a small team. As the project grows:

- Token rotation without a full redeploy becomes important for a live game.
  The ADR-0001 followup (SQLite-backed token store with a CLI tool) is the
  right next step — avoid building a token rotation API before you need one.
- For a team (vs. single developer), sops or a secrets manager
  (e.g., DO's managed secret storage, or AWS Secrets Manager / HashiCorp
  Vault if the cloud shifts) replaces the local `~/.config/sask/` approach.
  The principle — secrets never in git — stays the same; only the mechanism
  changes.
- The `no_log: true` Ansible discipline and the 0600 file permissions on the
  droplet are correct regardless of scale.

### Deployment pipeline

`scripts/deploy.sh` is a single-developer tool that prompts for confirmation
and runs sequentially. For production:

- The same Ansible playbook structure works; it just gets invoked by a CI/CD
  pipeline rather than a shell script. The idempotency work done in PR-004
  is what makes this safe — a pipeline can re-run the playbook without
  fear of unintended changes.
- Blue/green or rolling deployment (bring up a new droplet, run the playbook
  against it, verify health, cut DNS over) follows naturally from the
  reserved IP + DNS pattern. Tofu handles the IP assignment swap.
- The acceptance test suite (`tests/acceptance/`) is the right shape for a
  pipeline gate: run it against the new droplet before cutting traffic.

### Service architecture for a desktop-client / cloud-service game

The sask architecture — stateless HTTP service, bearer-token auth,
resource delivery by kind and ID — maps cleanly to the resource-delivery
layer of a game:

- The client (desktop) holds a session token; the server validates it on
  each request. No browser security model, no CORS, no cookie complexity.
  The `hmac.compare_digest` pattern is correct and sufficient.
- For game state (player position, session state, etc.), a separate service
  is cleaner than bolting it onto the resource server. The sask pattern
  (explicit routes, explicit translators, env-var configuration) is reusable.
- Gunicorn with worker tuning (`--workers` based on CPU count) handles
  moderate concurrency without architectural changes. For a game with many
  simultaneous players, async (e.g., moving to Starlette or FastAPI with
  ASGI) or a connection-oriented protocol (WebSocket) would be the next step
  — but start synchronous and measure first.
- Caddy's auto-TLS is production-grade for HTTPS. For a game client that
  connects directly to a service hostname, this is all you need. Rate limiting
  can be added as a Caddy directive with minimal configuration.

### Hardening checklist

The items explicitly deferred in ADR-0005 and the PR-004 spec are the
right production backlog:

| Area | Current state | Production step |
|------|--------------|-----------------|
| Secrets at rest | `tokens.toml` plaintext 0600 | sops or secrets manager |
| Token rotation | Full redeploy required | SQLite token store + CLI tool |
| Auth scopes | Single-tier (valid/invalid) | Per-client scopes in token store |
| Audit logging | Caddy access log only | App-layer logging per authenticated request |
| Rate limiting | None | Caddy `rate_limit` directive or app middleware |
| Defense in depth | DO firewall only | Add ufw on droplet for belt-and-suspenders |
| Monitoring | None | Uptime check (e.g., UptimeRobot) + systemd service alerting |
| Backups | None | Scheduled snapshots of droplet or data directories |
| Log rotation | Default journald | `logrotate` config for Caddy and gunicorn output |
| Multi-environment | Single deployment | Tofu workspaces + separate inventory for staging |

None of these require rearchitecting the service. They are additive layers
on top of the patterns already established. That's the point of getting the
foundation right first.

### What the spec-driven workflow gives you at production scale

At production scale, the ADR + requirements + PR spec workflow becomes more
valuable, not less. Every ADR records not just the decision but the
alternatives rejected and the consequences accepted. When a consequence
becomes a problem (e.g., "local state file lost"), the ADR already documents
the migration path. When a new developer asks why there's no Pydantic, ADR-0002
answers the question without requiring anyone to reconstruct the reasoning.

The PR spec format — explicit scope, explicit acceptance criteria, explicit
out-of-scope items — prevents scope creep and makes review tractable. For a
production gaming service where reliability matters, this discipline is not
overhead; it's how you avoid deploying half-finished features.

---

## 5. Addendum: NixOS, Claude, and Claude Code as development tools

### NixOS as the development platform

The project's dev environment is defined entirely in `flake.nix`. Every tool
used during development — `python`, `poetry`, `ruff`, `tofu`, `ansible`,
`ssh`, `sqlite`, `jq`, `curl` — is declared in the flake and pinned via the
Nix lock file. `nix develop` reproduces the environment exactly, on any
machine running Nix.

This matters for the same reason that infrastructure as code matters: the
development platform itself becomes transferable and recreatable. If the
development machine is lost or replaced, running `nix develop` in the
repository restores the full working environment without hunting for the
right version of each tool. There are no "works on my machine" gaps between
environments. For a project where the explicit goal is reproducibility
end-to-end, having the dev environment under the same discipline as the
deployment target is consistent and correct.

One practical friction point surfaced: NixOS does not allow Poetry-installed
binaries (e.g., `ruff`) to run directly, because Nix's store paths break
the assumptions those binaries make about their environment. The fix —
adding `ruff` to the flake packages rather than relying on `poetry run ruff`
— is a one-time cost that removes the friction permanently. Future tools
added to the project should be added to `flake.nix` first.

### Claude (Anthropic) as a design and drafting assistant

Claude (Anthropic Opus 4.7) was used throughout the project as an assistant
for design and documentation work: drafting Architecture Decision Records,
shaping requirements statements, writing PR specifications, and producing
initial versions of bash scripts and configuration file templates (Ansible
roles, Caddyfiles, systemd unit templates, Tofu HCL).

The developer brings 40 years of experience designing and building large-scale
financial data systems — the kind of background that produces strong instincts
about correctness, reliability, separation of concerns, and the cost of
getting foundational decisions wrong. Claude functioned as a capable
collaborator for articulating and structuring those instincts into the project's
formal artifacts, and for generating technically sound first drafts of
infrastructure code in domains (Ansible, Caddy, OpenTofu) where the
developer was building new familiarity.

The working model: the developer made the decisions; Claude drafted the
documents and templates that expressed them; the developer reviewed,
corrected, and approved. This kept the human in the loop on every consequential
choice while reducing the friction of producing well-structured written
artifacts from scratch. The spec-driven workflow (ADRs, requirements, PR specs)
was particularly well suited to this mode — each document had a clear
structure and purpose, which made Claude's drafts predictable and reviewable.

### Claude Code as the implementation agent

Claude Code was used to implement each PR spec: writing application code,
Ansible roles, Tofu configuration, and test suites against the
decisions and acceptance criteria already established in the TOML spec files.

The quality of Claude Code's output was directly proportional to the quality
of the specs it was given. Well-crafted ADRs (clear decision, clear rationale,
explicit consequences) and PR specs (explicit scope, explicit out-of-scope,
explicit acceptance criteria) gave Claude Code the context needed to implement
correctly on the first attempt in most cases. Where ambiguity existed in the
spec, it surfaced as implementation friction — which is the right outcome:
the ambiguity was resolved in the spec, not worked around in the code.

The main lesson for using Claude Code effectively in this kind of project:
treat it as a capable engineer who needs a clear brief. The upfront investment
in writing precise specs returned dividends in implementation quality and
reduced back-and-forth. The PR spec format — with explicit `scope.in`,
`scope.out`, `acceptance`, and `notes.for_assistant` sections — proved
well suited to this way of working. The `notes.for_assistant` section in
particular allowed the developer to pre-answer the questions a capable
engineer would naturally ask before starting.

---

## 6. Testing methodology: a frank reckoning

Let's be direct about this: incomplete testing is a form of technical debt
that eventually gets paid by the wrong people — users. A development approach
that relies on end-user beta testing to find defects is not a methodology;
it is an abdication. This project applied a layered testing discipline
throughout, and the record of what it caught and prevented is instructive.

### The layers

Testing in this project operated at four distinct levels, each with a
different scope and purpose. Skipping any layer means defects can propagate
to the next one, where they are harder and more expensive to catch.

**Layer 1: Unit tests** (PR-002, `tests/`)

Twenty-one pytest tests covering the application contract in isolation, using
Flask's test client — no network, no real token file, no real manifest on disk.
Every contract item was covered: health endpoint with and without auth, bearer
token validation (missing, malformed scheme, wrong value, correct value), each
resource kind (image, JSON, audio), unknown IDs, unknown kinds, and the shape
of error response bodies.

The key discipline here is negative-path coverage. It is easy to write tests
that only exercise the happy path (valid token, known ID, returns 200). The
negative paths — what the service does when something is wrong — are equally
part of the contract and must be tested explicitly. A `401` on a missing token
is a feature, not an error condition. Test it.

```
tests/test_auth.py::test_missing_token_returns_401        PASSED
tests/test_auth.py::test_wrong_token_returns_401          PASSED
tests/test_auth.py::test_malformed_auth_scheme_returns_401 PASSED
tests/test_auth.py::test_valid_token_does_not_return_401   PASSED
tests/test_auth.py::test_401_body_is_json                  PASSED
```

These tests ran in 0.23 seconds. There is no excuse for not running them on
every change.

**Layer 2: Bash smoke test** (`scripts/acceptance-test.sh`)

A fast, human-readable sanity check against the live HTTPS endpoint. Nine
assertions: health, missing token, bad token, unknown ID, each of the four
resource types, and byte-identity of one resource against the local file.
Designed to run in seconds and be readable without a pytest report. Useful
during active deployment debugging when you need a quick signal.

```
PASS: health endpoint returns 200
PASS: missing-token returns 401
PASS: bad-token returns 401
PASS: unknown-id returns 404
PASS: GET image/splash returns 200
PASS: GET json/scenario-001 returns 200
PASS: GET audio/ambient-loop returns 200
PASS: GET audio/ambient-video returns 200
PASS: splash.png byte-identical between local and remote
```

The byte-identity check is not cosmetic. It catches content corruption, wrong
file being served, encoding issues, and truncation. It is one assertion that
validates the entire delivery pipeline end-to-end.

**Layer 3: Pytest acceptance suite** (`tests/acceptance/test_remote.py`)

Seventeen tests against the real HTTPS endpoint, using the `requests` library
(not Flask's test client). These tests exercise the same contract as the unit
tests but through the full stack: DNS resolution, TLS termination, Caddy
reverse proxy, gunicorn, Flask application, file system. A unit test cannot
catch a Caddyfile misconfiguration or a systemd environment variable that
didn't make it to the process. An acceptance test can and does.

```
tests/acceptance/test_remote.py::test_tls_certificate_is_valid      PASSED
tests/acceptance/test_remote.py::test_404_body_is_json_with_error_key PASSED
tests/acceptance/test_remote.py::test_image_bytes_match_local         PASSED
... (17/17)
```

Note `test_tls_certificate_is_valid`: this test passes only if `curl` (or
`requests`) can verify the certificate without `-k`. A valid Let's Encrypt
certificate, correctly served, is a testable property. Test it.

Note `test_image_bytes_match_local`: this test fetches the image over HTTPS
and compares it byte-for-byte to the local file. It is the same assertion as
the bash smoke test, expressed in pytest for repeatability and CI integration.
Two ways to test the same thing is not redundancy; it is defense in depth.

**Layer 4: Operational acceptance tests** (manual, scripted, documented)

Some properties of a deployed system cannot be tested with `pytest`. They
require deliberate operational exercises:

- **Kill/restart test**: the gunicorn master process was killed with `kill -9`.
  Systemd restarted the service in 6 seconds (`RestartSec=5s` plus process
  startup). The service responded correctly immediately after restart. This
  validates `Restart=on-failure` actually works — not just that it is
  configured, but that it fires and recovers correctly under real conditions.

- **Idempotency test**: `scripts/deploy.sh -y` was run twice consecutively
  after convergence. Both runs produced `changed=0` across all Ansible tasks.
  This validates that the deployment is safe to re-run — critical for a
  deployment tool that will be used for day-two operations, not just initial
  setup.

- **Destroy + reprovision + redeploy cycle**: the entire cloud infrastructure
  was destroyed and rebuilt from zero. A fresh droplet was provisioned, the
  service deployed, and the full acceptance suite run against the new endpoint.
  17/17 tests passed without any manual intervention. This validates the
  system's recoverability claim, not just its initial deployment claim.

Each of these was documented with exact commands, timing, and output in
`tests/results/PR-004.md`. A test that was performed but not recorded is
a test that cannot be audited, repeated, or handed to another person.

### What this methodology prevents

**It prevents "it works on my machine."** The unit tests use Flask's test
client against the same application code that runs in production. The
acceptance tests run against the actual deployed service. There is no
"my machine" in the acceptance suite.

**It prevents discovering defects in production.** The byte-identity check
caught nothing in this project — because the implementation was correct.
That is the point. The check exists so that if something ever goes wrong
in the delivery pipeline, it is caught by a test run, not by a user reporting
corrupted assets.

**It prevents false confidence from incomplete test suites.** A suite of
21 unit tests that only test happy paths is not 21 tests; it is a smaller
number of tests wearing a larger number's clothes. Coverage of negative
paths, error bodies, content types, and byte integrity is what makes the
number meaningful.

**It prevents operational surprises.** The kill/restart test and the
destroy+reprovision cycle were not afterthoughts. They were acceptance items
in the PR-004 spec, planned before implementation began. Operational behavior
— how the system responds to failure, how it recovers, how it behaves on
re-deployment — is part of the contract and must be tested like any other
part of the contract.

### The standard to hold yourself to

If a property of the system matters — if you would be embarrassed or harmed
by it being wrong — it should be tested. The question to ask about every
acceptance criterion in a PR spec is: "How will I know, with evidence I can
show someone else, that this is true?" If the answer is "I'll just check
manually and remember that it worked," that is not an acceptance test; it is
a hope.

End users should experience a system that has already been verified to work.
Testing is the work that earns that confidence. There are no shortcuts that
do not eventually present themselves as someone else's problem.
