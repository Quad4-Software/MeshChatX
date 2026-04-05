.PHONY: install run build lint test test-be-perf clean

install:
	pnpm install
	poetry install

run:
	poetry run meshchat

build:
	pnpm run build

lint:
	pnpm run lint
	poetry run ruff check .
	poetry run ruff format --check .

test:
	pnpm run test
	poetry run python -m pytest tests/backend --ignore=tests/backend/test_performance_hotpaths.py --cov=meshchatx/src/backend

test-be-perf:
	poetry run python -m pytest tests/backend/test_performance_hotpaths.py

clean:
	rm -rf node_modules build dist python-dist meshchatx/public build-dir out
