#!/usr/bin/env bash
# SSH into the provisioned droplet using the Tofu-generated SSH config.
set -euo pipefail
exec ssh sask-droplet "$@"

