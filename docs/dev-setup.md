# Dev environment setup — sask

From-scratch procedure for Ubuntu 26.04 LTS (or any Debian-style Linux).
Replaces `docs/vm-setup.md`, which covered the retired NixOS `sask-dev` VM.

The system Python on Ubuntu 26.04 is 3.14. The project deliberately uses
3.12 via pyenv — the pin pre-dates 3.14 support validation in Werkzeug and
gunicorn. See DD-0019 for full rationale.

---

## 1. Clone the repo

```bash
git clone git@github.com:genuinemerit/sask.git
cd sask
```

## 2. Bootstrap the dev host (one command)

```bash
bash tools/dev/init-dev-host.sh
```

This installs all system-level prerequisites (see below for the list),
pyenv, Python 3.12 (latest patch), and Poetry. It is idempotent — safe to
re-run. It writes a `.python-version` file in the repo root that pins the
project to 3.12 without touching the system interpreter.

**System-prereq list (for reference / manual runs):** Empirically derived on
Ubuntu 26.04; see docs/devlog.md 2026-06-30. Native watch-items (libsqlite3,
libssl) confirmed: `import sqlite3, ssl, hashlib` passes with no extras.

```bash
# pyenv build dependencies
build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev
libsqlite3-dev libncursesw5-dev xz-utils tk-dev libxml2-dev
libxmlsec1-dev libffi-dev liblzma-dev

# runtime / harness / dev tooling
git curl wget ca-certificates openssh-client shellcheck tree ansible rsync golang-go

# deploy harness
snap install opentofu --classic

# xcaddy — not packaged in apt; builds the custom Caddy binary (with the
# rate-limit plugin) the deploy harness ships to the droplet
go install github.com/caddyserver/xcaddy/cmd/xcaddy@latest
```

## 3. Install Python dependencies

```bash
poetry install
```

Verify the interpreter and venv:

```bash
python --version      # should print: Python 3.12.x
poetry env info       # venv path at ~/.cache/pypoetry/virtualenvs/...
```

## 4. Run the test suite

```bash
poetry run pytest -q
```

All tests should pass. The count grows with each SPEC; check
`docs/devlog.md` for the most recent recorded passing count.

## 5. Run the app locally

```bash
PYTHONPATH=src poetry run flask --app sask.web run
```

Then open <http://localhost:5000/>. The `/health` route returns
`{"status": "ok"}` and is useful for scripted checks.

## 6. Run the app as a dev systemd service (log parity with prod)

Mirrors production's stdout → journald path (DD-0021, SPEC-033), so
`journalctl` — and the CLI's `logs query` command — behave the same way in
dev as they do on the droplet. This is optional for day-to-day work; use it
when you specifically want to validate logging behavior or exercise a
journal-querying command against a real journal.

```bash
bash tools/dev/sask-dev-service.sh install   # writes ~/.config/systemd/user/sask-dev.service
bash tools/dev/sask-dev-service.sh enable
bash tools/dev/sask-dev-service.sh start
```

Retrieve logs:

```bash
bash tools/dev/sask-dev-service.sh logs        # last 50 lines
bash tools/dev/sask-dev-service.sh logs 200     # last 200 lines
bash tools/dev/sask-dev-service.sh tail         # follow
# or directly:
journalctl --user -u sask-dev
```

`install` checks whether lingering is enabled for your account and tells you
either way — lingering (`loginctl enable-linger $USER`) keeps the user
systemd instance (and this service) running independent of active login
sessions; without it, `sask-dev.service` stops when your last session ends.
This is standard systemd behavior (see `systemd-logind(8)`), not sask-specific
— enable it yourself if you want the dev service to persist across logout.

**When to use which:** the direct-run path below (step 5,
`tools/dev/start_web.sh`) is faster for iterating on code — Flask's reloader
restarts on save and output prints straight to your terminal. Use the
systemd-service path when you need a real journal to query (journald-backed
`journalctl`/`logs query`), matching what's available on the droplet.

Stop it when you're done:

```bash
bash tools/dev/sask-dev-service.sh stop
```

## 7. Run pre-commit checks

Before every commit:

```bash
bash tools/dev/pre-commit-check.sh
```

Every check must exit 0.

## 8. SASK_ENV — enable dev-tier CLI commands

`SASK_ENV`, set alongside `SASK_LOG_LEVEL`/`SASK_LOCALE` in your shell
profile, is the CLI's dev/non-dev signal (DD-0025). With `SASK_ENV=dev`, the
CLI's dev-tier commands — thin wraps of the same scripts above
(`check_page_staleness`, `pre-commit-check`, `run-tests`, `start_web`,
`verify-clean-env`, `verify-do-secrets`, `validate_specs`, `validate_i18n`)
— appear in `sask --help` and run; without it they're hidden and refuse to
run with a clean error. Player- and admin-tier commands are unaffected
either way.

```bash
export SASK_ENV=dev   # add to your shell profile for day-to-day dev work
sask --help            # dev-tier commands now listed under "Dev"
sask pre-commit-check  # same script as `bash tools/dev/pre-commit-check.sh`
```

---

## Host secrets (manual)

Two secrets are required to use the DigitalOcean deploy harness. They are
**never scripted or committed** — place them manually after step 2.

### DIGITALOCEAN_TOKEN

```bash
mkdir -p ~/.config/sask
cp secrets/infra.env.example ~/.config/sask/infra.env
# Edit ~/.config/sask/infra.env and set DIGITALOCEAN_TOKEN to a valid DO
# personal access token (read/write scopes for Droplets, Reserved IPs,
# Firewalls, Domain Records, SSH Keys).
```

### sask_ed25519 SSH key

The DO ssh-key resource trusts a specific keypair. Copy the existing key
from the previous dev host rather than generating a new one (a new key would
require updating the DO ssh-key resource and the droplet's authorized_keys).

```bash
# From old host to new host:
scp <old-host>:~/.ssh/sask_ed25519 ~/.ssh/sask_ed25519
scp <old-host>:~/.ssh/sask_ed25519.pub ~/.ssh/sask_ed25519.pub
chmod 600 ~/.ssh/sask_ed25519
```

Also ensure `~/.ssh/config` (or `~/.ssh/config.d/sask`) has the
`sask-droplet` alias pointing to the correct IP with `IdentityFile
~/.ssh/sask_ed25519`.

### Verify secrets

```bash
bash tools/dev/verify-do-secrets.sh
```

All 4 checks (infra.env, token format, DO API HTTP 200, SSH to
`sask-droplet`) must pass.

---

## Verify the full setup

```bash
bash tools/dev/verify-clean-env.sh
```

Confirms: pyenv + Python 3.12 pin, native stdlib modules (sqlite3/ssl/hashlib),
poetry install, full test suite pass, app boot + `GET /health` returns 200.
