# Compatibility shim — Taskfile.yml owns install, lint, test, and build targets.
# Tree RSM targets call shell scripts directly so Make works without Task.
TASK ?= task

.DEFAULT_GOAL := help

.PHONY: install install-offline run dev dev-fe build format lint test test-be-perf clean help dist-linux dist-linux-x64
.PHONY: tree-manifest tree-rsm-sign tree-rsm-verify hooks-install

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

tree-manifest:
	sh scripts/ci/tree-manifest.sh generate

tree-rsm-verify:
	sh scripts/ci/verify-tree-rsm.sh

tree-rsm-sign:
	sh scripts/ci/sign-tree-rsm.sh

hooks-install:
	sh scripts/ci/install-git-hooks.sh

help:
	@echo "Makefile targets (most delegate to Task, see: task --list)."
	@echo "  make tree-rsm-verify  Verify meshchatx.rsm (no Task required)"
	@echo "  make tree-rsm-sign    Sign tree inventory (requires RNS_ID_PATH)"
	@echo "  make hooks-install    Enable .githooks pre-commit"
	@$(TASK) --list
