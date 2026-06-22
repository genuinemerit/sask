# Test results: SPEC-023

**Spec:** SPEC-023 — Service deployment via Ansible (platform / caddy / app roles)
**Date:** 2026-06-22
**Status:** PARTIAL — deployed and verified end-to-end against the real
droplet; the full destroy -> reprovision -> redeploy cycle is deferred to
SPEC-024's Layer 4, same as SPEC-022.

---

## Local validation (before touching the droplet)

```text
$ ansible-lint ansible/
Passed: 0 failure(s), 0 warning(s) on 18 files. Last profile that met the
validation criteria was 'production'.

$ ansible-playbook bootstrap.yml --syntax-check && ansible-playbook site.yml --syntax-check
(both clean)

$ xcaddy build --with github.com/mholt/caddy-ratelimit --output ...
$ caddy validate --config <rendered Caddyfile> --adapter caddyfile
Valid configuration
```

`ansible-lint` caught a real idempotency bug before it ever reached the
droplet: a `pip state=latest` task that would report false "changed" on
every run as new pip releases ship. Removed (the venv's bundled pip is
sufficient).

## First real deploy (tools/deploy.sh)

Two real bugs surfaced only by running for real, both fixed and re-verified:

1. **rsync can't create two missing destination directory levels at
   once.** `base` only creates `app_root` itself; the first sync to
   `app_root/src/sask/` failed because `app_root/src/` didn't exist yet.
   Fixed with an explicit directory-creation task before the sync.
2. **A later task's failure swallowed an earlier handler's restart.** The
   first run's app-role rsync failure aborted the play *before* the
   end-of-play handler flush, so the already-written sshd hardening
   (`PermitRootLogin no`) and Caddy's queued restart never actually took
   effect on the running services - the files were correct, but nothing
   had reloaded them. Root login still worked and Caddy was `enabled` but
   never `started` (zero journal entries). Fixed two ways: `meta:
   flush_handlers` immediately after the sshd-hardening task (so a later
   failure can't strand it again), and `state: started` added to both the
   `sask` and `caddy` service-enable tasks (decouples "is it running" from
   "did a config-change handler happen to fire"). The live droplet's stuck
   state was corrected with one manual `sudo systemctl restart ssh` after
   the fix landed, since the on-disk config was already correct — only the
   running process needed to catch up.
3. **A third issue, found and fixed before any of the above:** `remote_user:
   root` in `bootstrap.yml` was silently outranked by `group_vars/all.yml`'s
   `ansible_user: dave` (a known Ansible precedence quirk) — the bootstrap
   play tried `dave@` before `dave` existed. Fixed with an explicit `vars:
   ansible_user: root` in the play, which does take precedence.

## Idempotency (two consecutive clean runs, no manual steps between them)

```text
=== RUN A ===
sask-droplet : ok=30  changed=0  unreachable=0  failed=0  skipped=1  rescued=0  ignored=0
=== RUN B (immediately after) ===
sask-droplet : ok=30  changed=0  unreachable=0  failed=0  skipped=1  rescued=0  ignored=0
```

Status: PASS.

## Security posture (REQ-SEC-003)

```text
$ ssh -o User=root sask-droplet true
root@<ip>: Permission denied (publickey).

$ ssh sask-droplet whoami
dave

$ systemctl show sask -p NoNewPrivileges,ProtectSystem,ProtectHome,PrivateTmp,User
User=sask
PrivateTmp=yes
ProtectHome=yes
ProtectSystem=strict
NoNewPrivileges=yes
```

Root login refused; `dave` (not the no-shell `sask` service user) is the
only working login; sandboxing directives confirmed *active* by systemd
itself, not just present in the unit file. Status: PASS.

## End-to-end HTTPS chain

```text
$ curl -sS -D - https://sask.davidstitt.net/health
HTTP/2 200
strict-transport-security: max-age=31536000; includeSubDomains
x-content-type-options: nosniff
x-frame-options: DENY
referrer-policy: no-referrer-when-downgrade
content-security-policy: default-src 'self'; frame-ancestors 'none'
server: gunicorn
via: 1.1 Caddy
{"status": "ok"}

$ curl -sS https://sask.davidstitt.net/ | grep -o 104548096103
104548096103
```

TLS validates with no `-k`; every configured security header present; the
real story_now pulse value renders end-to-end (DNS -> TLS -> Caddy ->
gunicorn -> Flask -> engine -> template) — not just a listening process.
Status: PASS.

## Rate limiting (REQ-SEC-003: tighter on the download route)

```text
$ for i in 1 2 3 4 5 6; do curl -s -o /dev/null -w "%{http_code} " \
    https://sask.davidstitt.net/ephemeris/download; done
400 400 400 400 429 429
```

First 4 requests reach the app (400 — no query params given, expected for
this lightweight probe); the 5th and 6th are rejected with 429, exactly
matching the configured `events: 4, window: 1m` download-zone budget.
Status: PASS.

## Kill/restart (REQ-OPS-015)

```text
$ sudo pkill -9 -f gunicorn
$ systemctl status sask
Active: active (running) since ...; 2s ago    # fresh PID
$ curl -s -o /dev/null -w "%{http_code}" https://sask.davidstitt.net/health
200
```

systemd restarted the killed process automatically (RestartSec=5); the
service answered correctly immediately after. Status: PASS.

---

## Acceptance criteria

| Item | Status |
| --- | --- |
| Second consecutive deploy reports `changed=0` across every task | PASS |
| Service runs as non-root `sask`, gunicorn on 127.0.0.1, sandboxing effective | PASS |
| Caddy serves valid TLS with configured headers; rate limit tighter on download route | PASS |
| sshd refuses root and password auth; unattended security upgrades enabled | PASS |
| `config/` resolves correctly; a known value renders end-to-end on the droplet | PASS |
| `redeploy.sh` runs the full chain with ordering guards intact | DEFERRED, SPEC-024 |
| No secret in Ansible logs; only `.example` template in the repo | PASS |

---

## Deviations and notes

- `ansible/bootstrap.yml` was added during implementation (not in the
  original spec draft) — see `design/specs/spec-023-ansible.toml`'s
  updated scope section for why it's structurally necessary.
- `tools/deploy.sh` must `cd ansible` before invoking `ansible-playbook` —
  Ansible only auto-loads `ansible.cfg` (and its relative `inventory=`
  path) from the current directory, not from the playbook file's own
  location. Caught by the first real run failing to match any host.
- The three bugs in this document were each found by actually running the
  deploy against the real droplet, not by local linting alone —
  `ansible-lint`'s "production" profile and `--syntax-check` both passed
  cleanly throughout, since none of the three were lint-detectable
  (a variable-precedence quirk, a multi-level rsync mkdir limit, and a
  handler-flush-timing gap are all runtime behaviors).
