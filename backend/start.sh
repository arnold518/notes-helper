#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Create venv if missing
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    .venv/bin/pip install -q -r requirements.txt
fi

ROOT_PREFIX=/absproxy/7999 exec .venv/bin/uvicorn main:app --host 0.0.0.0 --port 7999 --reload
