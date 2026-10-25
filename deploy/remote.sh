#!/usr/bin/env bash
# Runs on the droplet after each rsync from CI.
set -euo pipefail
cd /opt/scanner

[ -d .venv ] || python3.15 -m venv .venv
.venv/bin/pip install -q -r requirements.txt

sudo systemctl restart scanner
sleep 3
curl -fsS -o /dev/null http://127.0.0.1:8000/docs && echo "scanner is up"
