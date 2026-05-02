# LXMFy Makefile
# Override SUDO for install target: make install SUDO=doas or leave unset to auto-detect

PYTHON_VERSION ?= 3.13
PACKAGE_NAME := lxmfy
DOCKER_IMAGE ?= lxmfy-test
WHEEL_BUILDER_IMAGE ?= lxmfy-wheel-builder

SUDO := $(shell command -v doas >/dev/null 2>&1 && echo doas || echo sudo)

.PHONY: default update install install-dev build clean test lint format check dev run
.PHONY: version bump-patch bump-minor bump-major update-version
.PHONY: docker docker-build docker-run docker-run-host docker-wheel-build docker-wheel-extract
.PHONY: docker-compose-build docker-compose-up docker-compose-down docker-compose-logs
.PHONY: docker-stop docker-clean publish-gitea publish-pypi publish all ci

default:
	@echo "Targets: update install install-dev build clean test lint format check dev run"
	@echo "         version bump-patch bump-minor bump-major docker docker-build docker-run"
	@echo "         docker-run-host docker-wheel-build docker-wheel-extract docker-stop docker-clean"
	@echo "         docker-compose-build docker-compose-up docker-compose-down docker-compose-logs"
	@echo "         publish-gitea publish-pypi publish all ci"

update:
	git pull

install:
	$(SUDO) pip install .

install-dev:
	poetry install
	poetry run pip install pytest pytest-asyncio pytest-cov

build:
	poetry build

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true

test:
	poetry run pytest tests/ -v

lint:
	poetry run ruff check .

format:
	poetry run ruff format .

check:
	poetry run safety check

dev:
	poetry install

run:
	poetry run lxmfy run echo

version:
	@python -c "import lxmfy; print(lxmfy.__version__)"

bump-patch:
	poetry version patch
	$(MAKE) update-version

bump-minor:
	poetry version minor
	$(MAKE) update-version

bump-major:
	poetry version major
	$(MAKE) update-version

update-version:
	@NEW_VERSION=$$(poetry version -s); \
	echo "__version__ = \"$$NEW_VERSION\"" > lxmfy/__version__.py; \
	echo "Updated version to $$NEW_VERSION"

docker: docker-build docker-run

docker-build:
	docker build -t $(DOCKER_IMAGE) .

docker-run:
	docker run -d \
	  --name $(DOCKER_IMAGE)-bot \
	  -v $(CURDIR)/config:/bot/config \
	  -v $(CURDIR)/.reticulum:/root/.reticulum \
	  --restart unless-stopped \
	  $(DOCKER_IMAGE)

docker-run-host:
	docker run -d \
	  --name $(DOCKER_IMAGE)-bot \
	  --network host \
	  -v $(CURDIR)/config:/bot/config \
	  -v $(CURDIR)/.reticulum:/root/.reticulum \
	  --restart unless-stopped \
	  $(DOCKER_IMAGE)

docker-wheel-build:
	docker build -f docker/Dockerfile.Build -t $(WHEEL_BUILDER_IMAGE) .

docker-wheel-extract:
	docker run --rm -v "$(CURDIR)/dist_output:/output" $(WHEEL_BUILDER_IMAGE)

docker-compose-build:
	docker-compose -f docker/docker-compose.yml build

docker-compose-up:
	docker-compose -f docker/docker-compose.yml up -d

docker-compose-down:
	docker-compose -f docker/docker-compose.yml down

docker-compose-logs:
	docker-compose -f docker/docker-compose.yml logs -f

docker-stop:
	docker stop $(DOCKER_IMAGE)-bot 2>/dev/null || true
	docker rm $(DOCKER_IMAGE)-bot 2>/dev/null || true

docker-clean: docker-stop
	docker rmi $(DOCKER_IMAGE) 2>/dev/null || true
	docker rmi $(WHEEL_BUILDER_IMAGE) 2>/dev/null || true

publish-gitea: build
	twine upload --repository-url https://git.quad4.io/api/packages/LXMFy/pypi dist/*

publish-pypi: build
	twine upload dist/*

publish: publish-gitea publish-pypi

all: clean lint test build

ci: lint check test build
