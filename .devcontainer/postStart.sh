#!/usr/bin/env bash
set -euo pipefail

# Stop any existing Flask server started by this script
pkill -f "flask run" >/dev/null 2>&1 || true

# Ensure we run from the repo root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Reset DB
python init_db.py

# Start Flask bound to all interfaces and log output
# Use nohup so it keeps running in the background
nohup python -m flask run --host 0.0.0.0 --port 5000 > .flask.log 2>&1 &

echo "Flask server starting on http://0.0.0.0:5000 (logs: $REPO_ROOT/.flask.log)"
