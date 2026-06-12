#!/bin/bash
# Linux / development launcher.
set -e
cd "$(dirname "$0")"
python3 -m venv .venv >/dev/null 2>&1 || true
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
exec python3 app.py
