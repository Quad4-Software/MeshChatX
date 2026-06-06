.PHONY: install install-offline run dev dev-fe build lint test test-be-perf clean help dist-linux dist-linux-x64

# Auto-detect offline bundle and configure caches
OFFLINE_BUNDLE := $(shell find vendor/offline -maxdepth 1 -type d -name 'meshchatx-offline-bundle-*' 2>/dev/null | head -n 1)

ifeq ($(MESHCHATX_OFFLINE_BUILD),1)
  ifneq ($(OFFLINE_BUNDLE),)
    export UV_CACHE_DIR := $(abspath $(OFFLINE_BUNDLE)/uv-cache)
    export ELECTRON_BUILDER_CACHE := $(abspath $(OFFLINE_BUNDLE)/electron-builder-cache)
  endif
endif

install:
ifeq ($(MESHCHATX_OFFLINE_BUILD),1)
	@if [ ! -d "node_modules" ]; then \
		echo "Error: node_modules not found for offline build." >&2; \
		echo "Run: bash scripts/install-offline.sh" >&2; \
		exit 1; \
	fi
	@echo "Offline build: skipping pnpm install (node_modules present)"
else
	pnpm install
endif
	uv sync --group dev $(if $(filter 1,$(MESHCHATX_OFFLINE_BUILD)),--offline)
	uv run python scripts/patch_lxst_pyogg_ogg_ctypes.py

install-offline:
	bash scripts/install-offline.sh

# Python backend only. For HMR, use: make dev  OR  make run in one terminal and pnpm run dev in another.
run:
	uv run python -m meshchatx.meshchat

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
	uv run ruff check .
	uv run ruff format --check .

test:
	pnpm run test
	uv run pytest tests/backend -n auto --cov=meshchatx/src/backend

test-be-perf:
	uv run pytest tests/backend/test_performance_hotpaths.py tests/backend/test_performance_bottlenecks.py

clean:
	rm -rf node_modules build dist python-dist meshchatx/public build-dir out
