#!/bin/bash
# Double-click me to start the Message Exporter (macOS).
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo ""
  echo "Python 3 isn't installed yet."
  echo "Install it one of these ways, then double-click run.command again:"
  echo "  1) Download it from https://www.python.org/downloads/  (easiest)"
  echo "  2) Or run:  xcode-select --install"
  echo ""
  read -r -p "Press Return to close this window..."
  exit 1
fi

echo "Setting things up (first run can take a minute)..."
python3 -m venv .venv >/dev/null 2>&1 || true
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo "Starting the Message Exporter..."
exec python3 app.py
