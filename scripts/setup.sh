#!/usr/bin/env bash
# AdaptiveSurgeon — one-command setup.
# Installs backend (Python venv) + frontend (npm) deps and seeds synthetic data.
# Fully offline-capable: every AI provider has a synthetic fallback.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> [1/4] Python virtual environment"
if [ ! -d ".venv" ]; then
  if python3 -m venv .venv 2>/dev/null; then
    echo "    created venv via python3 -m venv"
  else
    echo "    python3-venv unavailable; falling back to 'virtualenv'"
    pip3 install --user --quiet virtualenv
    "$(python3 -c 'import site,os;print(os.path.join(site.USER_BASE,"bin","virtualenv"))')" .venv
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
