EDITOR ?= nano
PYTHON ?= python3
PIP ?= pip
PREFIX ?= /usr/local
DESTDIR ?=
RNID_ID ?= e46112d44649266d71fe2193e00a4710
RNID_KEY ?= $(HOME)/.rngit/client_identity
RNS_REMOTE ?= rns://06a54b505bb67b25ef3f8097e8001edc/public/rns-filesync
TAG ?= v1.0.0

VERSION := $(shell $(PYTHON) -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])" 2>/dev/null || $(PYTHON) -c "from rns_filesync._meta import __version__; print(__version__)")
BUILD_DATE := $(shell date -u +%Y-%m-%dT%H:%M:%SZ)
GIT_COMMIT := $(shell git rev-parse --short HEAD 2>/dev/null || echo unknown)
GIT_DIRTY := $(shell git diff --quiet 2>/dev/null && echo 0 || echo 1)

.PHONY: all clean meta build wheel sdist sign upload release release-rns tag retag \
	test test-live test-services test-bwrap install install-user man uninstall version help

all: build

help:
	@echo "Targets: meta build wheel sdist test test-services install install-user man clean release"
	@echo "Version: $(VERSION)  commit: $(GIT_COMMIT)  built: $(BUILD_DATE)"

version: meta
	@$(PYTHON) -c "from rns_filesync._meta import version_string; print(version_string())"

meta:
	VERSION="$(VERSION)" BUILD_DATE="$(BUILD_DATE)" GIT_COMMIT="$(GIT_COMMIT)" GIT_DIRTY="$(GIT_DIRTY)" \
		$(PYTHON) scripts/bake_meta.py

clean:
	rm -rf dist/ build/ *.egg-info .pytest_cache .coverage htmlcov
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

build: meta wheel sdist

wheel: meta
	$(PYTHON) -m build --wheel

sdist: meta
	$(PYTHON) -m build --sdist

sign: build
	for f in dist/*.tar.gz dist/*.whl; do \
		rnid -f -i $(RNID_KEY) -s "$$f" -w "$$f.rsg"; \
	done

upload: sign
	twine upload dist/*.whl dist/*.tar.gz

release: tag release-rns

release-rns: sign
	mkdir -p dist
	RELEASE_TAG=$(TAG) EDITOR="$(EDITOR)" \
		rngit release -i $(RNID_KEY) $(RNS_REMOTE) create $(TAG):./dist

tag:
	@if git rev-parse -q --verify "refs/tags/$(TAG)" >/dev/null 2>&1; then \
		echo "Tag $(TAG) already exists. Use: make retag TAG=$(TAG)"; \
		echo "Or republish rngit only: make release-rns TAG=$(TAG)"; \
		exit 1; \
	fi
	git tag -s $(TAG) -m "$(TAG)"
	git push origin $(TAG)

retag:
	git tag -d $(TAG) 2>/dev/null || true
	-git push origin :refs/tags/$(TAG) 2>/dev/null || true
	git tag -s $(TAG) -m "$(TAG)"
	git push origin $(TAG)

test:
	$(PYTHON) -m pytest -m "not exploratory and not live"

test-live:
	$(PYTHON) -m pytest -m live

test-services:
	./packaging/docker-test/run-all.sh

test-bwrap:
	./packaging/docker-test/test-bwrap.sh

install: meta
	$(PIP) install --break-system-packages .
	$(MAKE) man

install-user: meta
	$(PIP) install --user .
	mkdir -p $(HOME)/.local/share/man/man1
	cp man/man1/rns-filesync.1 $(HOME)/.local/share/man/man1/

man:
	mkdir -p $(DESTDIR)$(PREFIX)/share/man/man1
	cp man/man1/rns-filesync.1 $(DESTDIR)$(PREFIX)/share/man/man1/

uninstall:
	$(PIP) uninstall -y rns-filesync || true
	rm -f $(DESTDIR)$(PREFIX)/share/man/man1/rns-filesync.1
	rm -f $(HOME)/.local/share/man/man1/rns-filesync.1
