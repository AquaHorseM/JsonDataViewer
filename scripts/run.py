#!/usr/bin/env bash
set -euo pipefail

# Allow PYTHON to be overridden: PYTHON=python3.11 ./scripts/run.sh file.json
PYTHON_BIN="${PYTHON:-python3}"

# Resolve repo root (script/..)
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"
exec "$PYTHON_BIN" -m jsonviewer "$@"
