#!/usr/bin/env bash
# AdaptiveSurgeon — one-command setup.
# Installs backend (Python venv) + frontend (npm) deps and seeds synthetic data.
# Fully offline-capable: every AI provider has a synthetic fallback.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> [1/4] Python virtual environment"
# Don't let a venv that the caller already activated interfere with creation.
unset VIRTUAL_ENV || true
if [ ! -f ".venv/bin/pip" ]; then
  rm -rf .venv
  if python3 -m venv .venv >/dev/null 2>&1 && [ -f ".venv/bin/pip" ]; then
    echo "    created venv via 'python3 -m venv'"
  else
    echo "    python3-venv (ensurepip) unavailable; falling back to 'virtualenv'"
    rm -rf .venv
    if ! command -v virtualenv >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/virtualenv" ]; then
      pip3 install --quiet virtualenv || python3 -m pip install --quiet --user virtualenv
    fi
    VENV_BIN="$(command -v virtualenv || echo "$HOME/.local/bin/virtualenv")"
    "$VENV_BIN" .venv
  fi
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> [2/4] Backend dependencies"
pip install --quiet --upgrade pip
pip install --quiet -r backend/requirements.txt

echo "==> [3/4] Frontend dependencies"
( cd frontend && npm install --no-audit --no-fund )

echo "==> [4/4] Seeding synthetic demo data (patients, videos, full analysis)"
( cd backend && python -m app.seed.demo )

echo ""
echo "Setup complete. Start the platform with:"
echo "    bash scripts/run_dev.sh      (or: make dev)"
