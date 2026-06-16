.PHONY: setup dev seed test smoke backend frontend build

setup:
	bash scripts/setup.sh

dev:
	bash scripts/run_dev.sh

seed:
	. .venv/bin/activate && cd backend && python -m app.seed.demo

backend:
	. .venv/bin/activate && cd backend && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev -- --host

test:
	. .venv/bin/activate && cd backend && pytest -q

smoke:
	bash scripts/smoke_test.sh

build:
	cd frontend && npm run build
