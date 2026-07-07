# LXMFy Makefile
# Override SUDO for install target: make install SUDO=doas or leave unset to auto-detect

PYTHON_VERSION ?= 3.13
PACKAGE_NAME := lxmfy
DOCKER_IMAGE ?= lxmfy-test
WHEEL_BUILDER_IMAGE ?= lxmfy-wheel-builder

RNGIT ?= rngit
RNGIT_CONFIG ?= $(HOME)/.rngit
RNS_CONFIG ?= $(HOME)/.reticulum
RNGIT_REMOTE ?= $(shell git config --get remote.origin.url)
RNGIT_IDENTITY ?=
RNGIT_SIGNER ?=
RNGIT_NAME ?=
RELEASE_TAG ?= v$(shell poetry version -s)
RELEASE_DIST ?= dist
RELEASE_ARTIFACT ?= all

SUDO := $(shell if command -v doas; then echo doas; else echo sudo; fi)

RNGIT_RELEASE = $(RNGIT) release --config $(RNGIT_CONFIG) --rnsconfig $(RNS_CONFIG)
RNGIT_RELEASE_OPTS = $(if $(RNGIT_IDENTITY),-i $(RNGIT_IDENTITY),) \
	$(if $(RNGIT_SIGNER),-s $(RNGIT_SIGNER),) \
	$(if $(RNGIT_NAME),-n $(RNGIT_NAME),)
RELEASE_TARGET = $(RELEASE_TAG):$(RELEASE_DIST)

PACKAGE_VERSION := $(shell poetry version -s)

.PHONY: default update install install-dev build clean test lint format typecheck check dev run
.PHONY: version bump-patch bump-minor bump-major update-version
.PHONY: docker docker-build docker-run docker-run-host docker-wheel-build docker-wheel-extract
.PHONY: docker-compose-build docker-compose-up docker-compose-down docker-compose-logs
.PHONY: docker-stop docker-clean publish-gitea publish-pypi publish all ci
.PHONY: release-dist release-dist-clean release-tag release-push release-local release-upload release
.PHONY: release-list release-view release-fetch release-verify release-delete

default:
	@echo "Targets: update install install-dev build clean test lint format typecheck check dev run"
	@echo "         version bump-patch bump-minor bump-major docker docker-build docker-run"
	@echo "         docker-run-host docker-wheel-build docker-wheel-extract docker-stop docker-clean"
	@echo "         docker-compose-build docker-compose-up docker-compose-down docker-compose-logs"
	@echo "         publish-gitea publish-pypi publish all ci"
	@echo "         release release-dist release-tag release-push release-local release-upload"
	@echo "         release-list release-view release-fetch release-verify release-delete"

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
	find . -type d -name __pycache__ -exec rm -rf {} + || true
	find . -type f -name "*.pyc" -delete || true
	find . -type f -name "*.pyo" -delete || true

test:
	poetry run pytest tests/ -v

lint:
	poetry run ruff check .

format:
	poetry run ruff format .

typecheck:
	poetry run pyright lxmfy

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
	docker stop $(DOCKER_IMAGE)-bot || true
	docker rm $(DOCKER_IMAGE)-bot || true

docker-clean: docker-stop
	docker rmi $(DOCKER_IMAGE) || true
	docker rmi $(WHEEL_BUILDER_IMAGE) || true

publish-gitea: build
	twine upload --repository-url https://git.quad4.io/api/packages/LXMFy/pypi dist/*

publish-pypi: build
	twine upload dist/*

publish: publish-gitea publish-pypi

release-dist-clean:
	@if [ -d dist ]; then \
		find dist -maxdepth 1 -type f ! -name '$(PACKAGE_NAME)-$(PACKAGE_VERSION)*' -print -delete; \
	fi

release-dist:
	rm -rf dist/
	poetry build

release-tag:
	@tag="$(RELEASE_TAG)"; \
	if git show-ref --verify --quiet "refs/tags/$$tag"; then \
		echo "Tag $$tag already exists"; \
	else \
		git tag -a "$$tag" -m "Release $$tag"; \
		echo "Created tag $$tag"; \
	fi

release-push: release-tag
	git push origin --follow-tags

release-local: release-dist
	$(RNGIT_RELEASE) $(RNGIT_RELEASE_OPTS) -L $(RNGIT_REMOTE) create $(RELEASE_TARGET)

release-upload: release-dist
	@test -n "$(RNGIT_REMOTE)" || (echo "RNGIT_REMOTE is empty; set it or configure git remote origin" && exit 1)
	$(RNGIT_RELEASE) $(RNGIT_RELEASE_OPTS) $(RNGIT_REMOTE) create $(RELEASE_TARGET)

release: release-dist release-tag release-push release-upload

release-list:
	@test -n "$(RNGIT_REMOTE)" || (echo "RNGIT_REMOTE is empty" && exit 1)
	$(RNGIT_RELEASE) $(RNGIT_REMOTE) list

release-view:
	@test -n "$(RELEASE_TAG)" || (echo "Set RELEASE_TAG=..." && exit 1)
	$(RNGIT_RELEASE) $(RNGIT_REMOTE) view $(RELEASE_TAG)

release-fetch:
	@test -n "$(RELEASE_TAG)" || (echo "Set RELEASE_TAG=... and optionally RELEASE_ARTIFACT=all" && exit 1)
	$(RNGIT_RELEASE) $(RNGIT_RELEASE_OPTS) $(RNGIT_REMOTE) fetch $(RELEASE_TAG):$(RELEASE_ARTIFACT)

release-verify:
	@test -n "$(RELEASE_TAG)" || (echo "Set RELEASE_TAG=... and optionally RELEASE_ARTIFACT=all" && exit 1)
	$(RNGIT_RELEASE) $(RNGIT_RELEASE_OPTS) -o $(RNGIT_REMOTE) verify $(RELEASE_TAG):$(RELEASE_ARTIFACT)

release-delete:
	@test -n "$(RELEASE_TAG)" || (echo "Set RELEASE_TAG=..." && exit 1)
	$(RNGIT_RELEASE) $(RNGIT_REMOTE) delete $(RELEASE_TAG)

all: clean lint typecheck test build

ci: lint typecheck check test build
