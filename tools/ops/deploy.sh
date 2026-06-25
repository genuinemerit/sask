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

bash tools/ops/export-requirements.sh

# cd into ansible/ rather than passing -i/--ANSIBLE_CONFIG explicitly:
# Ansible only auto-loads ansible.cfg (and its relative inventory= path)
# from the current directory, not from the playbook's own location.
cd ansible

if ! ssh -o BatchMode=yes -o ConnectTimeout=5 sask-droplet true 2>/dev/null; then
    printf '[INFO] dave not yet reachable — running the one-time root bootstrap.\n'
    ansible-playbook bootstrap.yml
fi

ansible-playbook site.yml
