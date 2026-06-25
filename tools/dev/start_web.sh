#!/usr/bin/env bash
# Start the sask Flask development server.
#
# Run this script on the sask-dev VM from the project root:
#
#   bash tools/dev/start_web.sh
#
# Before running, open an SSH tunnel from the Ubuntu host so the browser
# can reach the server:
#
#   ssh -L 5000:localhost:5000 sask-dev
#
# Then open http://localhost:5000/ in a browser on the Ubuntu host.

set -euo pipefail

cd "$(dirname "$0")/../.."
PYTHONPATH=src .venv/bin/flask --app sask.web run
