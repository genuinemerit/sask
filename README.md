# sask

Umbrella project for the Saskan calendar engine and related tools.
This repository is a deliberate evolutionary rebuild: lean scaffolding first,
functional areas added incrementally under `/src`.

## Quick start

**Prerequisites:** Ubuntu 26.04 LTS (or Debian-style Linux). See
[docs/dev-setup.md](docs/dev-setup.md) for the full procedure.

```bash
git clone https://github.com/genuinemerit/sask.git
cd sask
bash tools/dev/init-dev-host.sh   # apt prereqs, pyenv, Python 3.12, Poetry
poetry install
```

Verify:

```bash
python --version    # 3.12.x (pyenv-pinned; system python3 is 3.14, untouched)
poetry --version
```

## Layout

```text
ansible/      Ansible playbooks deploying the app onto the production droplet
config/       TOML engine configuration (time constants, calendars, seasons, timeline)
design/       TOML design docs (decisions/, reqs/, specs/)
docs/         living documents and guides
infra/        infra/archive/ (retired NixOS artifacts) and infra/tofu/ (production droplet IaC)
assets/       local (dev/artist staging) + versioned (v0, deploy-ready) binary assets — see DD-0016
secrets/      local credentials — git-ignored except README.md and *.example
src/          Python source (package: sask)
tests/        pytest suites and test results
tools/        developer tooling and deploy orchestration (see docs/deploy-runbook.md)
```

## Web app

Five browser pages are available locally or live at
[sask.davidstitt.net](https://sask.davidstitt.net).

| Page | Description |
|---|---|
| `/` | Pulse lookup — enter a pulse and see Astro day, time of day, orbital position |
| `/moons` | Moons sky view — phase, illumination, albedo, eclipse, altitude/azimuth, rise/transit/set for all 8 moons |
| `/planets` | Planets sky view — same columns plus colour, brightness, and telescopic detail for all 7 planets |
| `/sky` | Unified sky for a date — lunar calendars, moons and wanderers above horizon, |
| | co-fullness, season, fixed stars and houses, night summary, image prompt; |
| | lore overlay: watch/shur/keyt time and era/Round/phase calendar dates |
| `/ephemeris` | Ephemeris generator — time-series of sky scenes at a configurable step; |
| | scribal and/or kinematic JSON preview with download links |

All pages accept four equivalent input forms: pulse number, Astro day,
Fatunik date, or Terpin date. After any query all four input fields are
cross-populated with the resolved equivalents. The `/ephemeris` page also
accepts a Duration (Days) field for date-mode ranges.

A language toggle sets the locale (en-US/es-ES) for tagged interface text,
localized engine results (e.g. season names), and parallel-translated help
pages, defaulting from the browser's `Accept-Language` (see DD-0022).

**Start the server:**

```bash
bash tools/dev/start_web.sh
```

Or manually (flask dev server):

```bash
PYTHONPATH=src poetry run flask --app sask.web run
```

Or with gunicorn:

```bash
PYTHONPATH=src poetry run gunicorn wsgi:app
```

## CLI

A `sask` console-script (DD-0021, DD-0025) wraps the same engine/spine
functions the web adapter uses, with commands tagged by role tier
(player/admin/dev — DD-0025) as an auth seam, and rendered with `rich`
(styled in a terminal, plain when piped/redirected):

```bash
poetry run sask --help
```

**Player** (read-only, always available):

| Command | Description |
|---|---|
| `sask convert --pulse N` | Astro day, day-pulse offset, orbital position for a pulse |
| `sask season --pulse N` | Astronomical season (and near-event) for a pulse, localized |
| `sask help [topic]` | Renders the same Markdown help content as the web `/help` route |
| `sask asset list` / `sask asset info <kind> <id>` | Asset catalog descriptor fields (no payload reads) |
| `sask host_info` | Non-sensitive host/platform diagnostics (no hostname/IP/MAC) |
| `sask validate_json SCHEMA DATA` | Generic JSON-Schema (Draft 2020-12) validation |

**Admin** (diagnostics/verification, no service mutation):

| Command | Description |
|---|---|
| `sask config check` | Read-only config validation |
| `sask logs query` | Query the app's structured journald logs |
| `sask logs verify` | Verify recent journal output: well-formed app JSON, no cleartext secrets |
| `sask acceptance-test` | Layer 2 acceptance suite against a live sask endpoint |
| `sask run_perf` | Layer 1 engine benchmarks |

`config`/`logs` are always available. `acceptance-test`/`run_perf` wrap
`tools/ops/` scripts, which aren't part of the deployed package (only
`src/sask/`, `config/`, assets, `docs/help/`, `wsgi.py` are synced to the
droplet) — they're hidden from `--help` wherever `tools/ops/` isn't
present (i.e. on the deployed droplet), since they could never succeed
there regardless of tier/auth.

**Dev** (development/build/verification tooling — only available with
`SASK_ENV=dev`; see `docs/dev-setup.md` §8), each a thin adapter over the
identically-named `tools/dev/` script:

`sask check_page_staleness`, `sask pre-commit-check`, `sask run-tests`,
`sask start_web`, `sask verify-clean-env`, `sask verify-do-secrets`,
`sask validate_specs`, `sask validate_i18n`.

`deploy`/`redeploy`/`set-log-level` are deliberately **not** CLI commands —
service/infrastructure mutation stays in `tools/ops/` (DD-0021).

`--lang <locale>` / `SASK_LOCALE` selects the locale for interface text and
localized results (mirrors `SASK_LOG_LEVEL`'s flag/env-var precedence); logs
and other operator-facing output are never localized.

## Pre-commit checks

Run before every commit; all checks must exit 0:

```bash
bash tools/dev/pre-commit-check.sh
```

## Testing

```bash
bash tools/dev/run-tests.sh                           # all tests, quiet
bash tools/dev/run-tests.sh -v                        # all tests, verbose
bash tools/dev/run-tests.sh --spec SPEC-002           # one spec, quiet
bash tools/dev/run-tests.sh --spec SPEC-002 -v --save # one spec, verbose, save results
```

## Design docs

Design decisions, requirements, and specs live under `/design` as TOML.
Validate them with:

```bash
python3 tools/dev/validate_specs.py
```

## Development environment

See [docs/dev-setup.md](docs/dev-setup.md) for the from-scratch Ubuntu setup.
Python is pinned to 3.12 via pyenv; all tooling is managed by Poetry.
`tools/dev/init-dev-host.sh` is the single-command system bootstrap.

## Deployment

The app runs live on a DigitalOcean droplet at
[sask.davidstitt.net](https://sask.davidstitt.net), provisioned with
OpenTofu (`infra/tofu/`) and configured with Ansible (`ansible/`). See
[docs/deploy-runbook.md](docs/deploy-runbook.md) for day-to-day operation
(connect, redeploy, full rebuild, full teardown, viewing logs) and
[design/decisions/dd-0014-deploy.toml](design/decisions/dd-0014-deploy.toml)
for the design.

The app logs structured JSON to stdout, viewable live via `journalctl`
(see the runbook's Logging section).
