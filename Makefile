# Compatibility shim - Taskfile.yml owns install, lint, test, and build targets.
TASK ?= task

.DEFAULT_GOAL := help

.PHONY: install install-offline run dev dev-fe build format lint test test-be-perf clean help dist-linux dist-linux-x64
.PHONY: ci-pr ci-docker

install:
	@$(TASK) install

install-offline:
	@$(TASK) install:offline

run:
	@$(TASK) run

dev:
	@$(TASK) dev

dev-fe:
	@$(TASK) dev-fe

build:
	@$(TASK) build

format:
	@$(TASK) format

lint:
	@$(TASK) lint

test:
	@$(TASK) test

test-be-perf:
	@$(TASK) test:be:perf

clean:
	@$(TASK) clean

dist-linux:
	@$(TASK) dist:linux

dist-linux-x64:
	@$(TASK) dist:linux-x64

ci-pr:
	bash scripts/ci/run.sh pr

ci-docker:
	bash scripts/ci/run-docker.sh pr

help:
	@echo "Makefile targets (most delegate to Task, see: task --list)."
	@echo "  make ci-pr            Portable PR CI (Forgejo, Gitea, local)"
	@echo "  make ci-docker        PR CI in scripts/ci/Dockerfile.ci (Podman or Docker)"
	@$(TASK) --list
