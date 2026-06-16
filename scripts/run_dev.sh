#!/usr/bin/env bash
# Start backend (FastAPI :8000) and frontend (Vite :5173) together.
# Ctrl-C stops both.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Backend  -> http://localhost:8000  (docs at /docs)"
( cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 ) &
BACK_PID=$!

echo "==> Frontend -> http://localhost:5173"
( cd frontend && npm run dev -- --host ) &
FRONT_PID=$!

trap 'echo; echo "Stopping…"; kill $BACK_PID $FRONT_PID 2>/dev/null || true' INT TERM
wait
