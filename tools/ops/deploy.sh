#!/usr/bin/env bash
# Deploy (or re-converge) sask onto an already-provisioned droplet via
# Ansible.
#
#   bash tools/ops/deploy.sh
#
# Requires ~/.config/sask/infra.env (outside the repo, see
# secrets/infra.env.example) as a general setup-sanity precondition, even
# though Ansible itself doesn't need the DO token. Bootstraps the `dave`
# admin account on first run only (when it isn't already reachable as
# dave); every later run skips straight to the main site play.

set -euo pipefail

cd "$(dirname "$0")/../.."

INFRA_ENV="$HOME/.config/sask/infra.env"
if [[ ! -f "$INFRA_ENV" ]]; then
    printf '[FAIL] %s not found.\n' "$INFRA_ENV" >&2
    printf '       Copy secrets/infra.env.example there and fill in your token.\n' >&2
    exit 1
fi

# Strict-mode i18n completeness gate (DD-0022, REQ-OPS-021): a declared
# locale missing translations for tags the base locale defines blocks
# deploy. Pre-deploy correctness check, same fail-fast-before-touching-
# infrastructure spirit as the INFRA_ENV check above — not a live-HTTP
# probe like acceptance-test.sh.
if ! python3 tools/dev/validate_i18n.py --strict; then
    printf '[FAIL] i18n validation failed (strict mode) — fix before deploying.\n' >&2
    exit 1
fi

# Full-text page staleness gate (DD-0023, SPEC-036's completeness_gate
# deliverable): a base page whose es-ES rendered page is stale or missing
# blocks deploy, same as a missing tag translation above. Deploy runs on
# the dev host, which has the poetry venv, so this can use the same
# non-bare invocation build_i18n_pages.py/check_page_staleness.py already
# require (see check_page_staleness.py's own docstring for why it isn't
# bare-python3-compatible like validate_i18n.py).
if ! poetry run python3 tools/dev/check_page_staleness.py; then
    printf '[FAIL] page staleness check failed — rebuild/re-review before deploying.\n' >&2
    exit 1
fi

bash tools/ops/export-requirements.sh

# Wait for the droplet's SSH daemon to come up before Ansible connects.
# A freshly created or recreated droplet can take ~60 s to be ready; not
# waiting here was the root cause of the SSH-readiness race flagged in the
# SPEC-029 addendum. Succeeds immediately when the droplet is already running.
#
# Tries both root and dave: a freshly provisioned droplet only has root;
# a droplet where a prior deploy.sh run got as far as the base role's sshd
# hardening (PermitRootLogin no) before failing later (e.g. mid-Caddy-build)
# only has dave. Checking root alone would wait the full 2 minutes and fail
# on that already-partially-deployed droplet even though SSH is fine.
_SSH_READY=false
for _I in $(seq 1 24); do
    if ssh -o BatchMode=yes -o ConnectTimeout=5 -o User=root sask-droplet true 2>/dev/null \
        || ssh -o BatchMode=yes -o ConnectTimeout=5 sask-droplet true 2>/dev/null; then
        _SSH_READY=true
        break
    fi
    printf '[INFO] SSH not ready yet (%d/24); retrying in 5 s...\n' "$_I"
    sleep 5
done
if [[ "$_SSH_READY" != true ]]; then
    printf '[FAIL] Droplet SSH did not become reachable within 2 minutes.\n' >&2
    exit 1
fi

# cd into ansible/ rather than passing -i/--ANSIBLE_CONFIG explicitly:
# Ansible only auto-loads ansible.cfg (and its relative inventory= path)
# from the current directory, not from the playbook's own location.
cd ansible

if ! ssh -o BatchMode=yes -o ConnectTimeout=5 sask-droplet true 2>/dev/null; then
    printf '[INFO] dave not yet reachable — running the one-time root bootstrap.\n'
    ansible-playbook bootstrap.yml
fi

ansible-playbook site.yml
