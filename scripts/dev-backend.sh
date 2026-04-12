#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${ULTRERP_DEV_HOST:-127.0.0.1}"
PORT="${1:-8000}"
PYTHON_BIN="${ULTRERP_BACKEND_PYTHON:-$ROOT_DIR/backend/.venv/bin/python}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Backend Python runtime not found at: $PYTHON_BIN" >&2
  echo "Run 'cd backend && uv sync' first, or set ULTRERP_BACKEND_PYTHON." >&2
  exit 1
fi

export PYTHONPATH="$ROOT_DIR/backend${PYTHONPATH:+:$PYTHONPATH}"

exec "$PYTHON_BIN" -m uvicorn app.main:create_app --factory --host "$HOST" --port "$PORT"