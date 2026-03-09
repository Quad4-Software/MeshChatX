.PHONY: install run build lint test clean

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
	poetry run pytest tests/backend --cov=meshchatx/src/backend

clean:
	rm -rf node_modules build dist python-dist meshchatx/public build-dir out
