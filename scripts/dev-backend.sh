#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${ULTRERP_DEV_HOST:-127.0.0.1}"
PORT="${1:-8000}"
PYTHON_BIN="${ULTRERP_BACKEND_PYTHON:-$ROOT_DIR/backend/.venv/bin/python}"

find_listener_pids() {
  lsof -tiTCP:"$PORT" -sTCP:LISTEN -nP 2>/dev/null || true
}

is_ultrerp_backend_command() {
  local command="$1"
  [[ "$command" == *"uvicorn"* ]] && [[ "$command" == *"app.main"* ]] && [[ "$command" == *".venv/bin/python"* || "$command" == *"UltrERP"* ]]
}

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Backend Python runtime not found at: $PYTHON_BIN" >&2
  echo "Run 'cd backend && uv sync' first, or set ULTRERP_BACKEND_PYTHON." >&2
  exit 1
fi

export PYTHONPATH="$ROOT_DIR/backend${PYTHONPATH:+:$PYTHONPATH}"

listener_pids="$(find_listener_pids)"
if [[ -n "$listener_pids" ]]; then
  while IFS= read -r pid; do
    [[ -z "$pid" ]] && continue
    command="$(ps -p "$pid" -o command=)"

    if ! is_ultrerp_backend_command "$command"; then
      echo "Port $PORT is already in use by a non-UltrERP process:" >&2
      echo "  PID $pid: $command" >&2
      echo "Stop it manually or choose another port." >&2
      exit 1
    fi

    echo "Replacing existing UltrERP backend on $HOST:$PORT (PID $pid)." >&2
    kill "$pid" 2>/dev/null || true
    if lsof -tiTCP:"$PORT" -sTCP:LISTEN -nP 2>/dev/null | grep -qx "$pid"; then
      kill -9 "$pid" 2>/dev/null || true
    fi
  done <<< "$listener_pids"

  if lsof -tiTCP:"$PORT" -sTCP:LISTEN -nP >/dev/null 2>&1; then
    echo "Port $PORT is still busy after replacing the existing backend." >&2
    exit 1
  fi
fi

echo "Starting UltrERP backend on http://$HOST:$PORT" >&2

exec "$PYTHON_BIN" -m uvicorn app.main:create_app --factory --host "$HOST" --port "$PORT"