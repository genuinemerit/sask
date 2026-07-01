#!/usr/bin/env bash
# Start the sask Flask development server.
#
# Run this script on the dev host (ubuvm) from the project root:
#
#   bash tools/dev/start_web.sh
#
# Before running, open an SSH tunnel from your local machine so the browser
# can reach the server:
#
#   ssh -L 5000:localhost:5000 ubuvm
#
# Then open http://localhost:5000/ in a browser on your local machine.

set -euo pipefail

cd "$(dirname "$0")/../.."
PYTHONPATH=src poetry run flask --app sask.web run
