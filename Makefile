.PHONY: install run dev dev-fe build lint test test-be-perf clean help dist-linux dist-linux-x64

install:
	pnpm install
	poetry install

# Python backend only. For HMR, use: make dev  OR  make run in one terminal and pnpm run dev in another.
run:
	poetry run python -m meshchatx.meshchat

# Vite dev server (live reload) + backend. Open http://localhost:5173 — proxies /api and /ws to MESHCHAT_PORT (default 8000).
dev:
	bash scripts/dev-local.sh

# Vite only; expects backend already running (e.g. make run on port 8000).
dev-fe:
	pnpm run dev -- --host 127.0.0.1 --port 5173

build:
	pnpm run build

# Linux AppImage + deb (see package.json dist:linux).
dist-linux:
	pnpm run dist:linux

dist-linux-x64:
	pnpm run dist:linux-x64

help:
	@echo "make dev        - Vite HMR + backend (http://localhost:5173)"
	@echo "make run        - backend only"
	@echo "make dev-fe     - Vite only (pair with make run)"
	@echo "make dist-linux - AppImage + deb (electron-builder)"
	@echo "Env: MESHCHAT_PORT, E2E_BACKEND_PORT (vite proxy; script sets both), VITE_DEV_HOST, VITE_DEV_PORT"

lint:
	pnpm run lint
	poetry run ruff check .
	poetry run ruff format --check .

test:
	pnpm run test
	poetry run python -m pytest tests/backend -n auto --cov=meshchatx/src/backend

test-be-perf:
	poetry run python -m pytest tests/backend/test_performance_hotpaths.py tests/backend/test_performance_bottlenecks.py

clean:
	rm -rf node_modules build dist python-dist meshchatx/public build-dir out
