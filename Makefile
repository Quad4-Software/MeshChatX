# Compatibility shim — Taskfile.yml owns install, lint, test, and build targets.
TASK ?= task

.DEFAULT_GOAL := help

.PHONY: install install-offline run dev dev-fe build lint test test-be-perf clean help dist-linux dist-linux-x64

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

lint:
	@$(TASK) lint:all

test:
	@$(TASK) test:all

test-be-perf:
	@$(TASK) test:be:perf

clean:
	@$(TASK) clean

dist-linux:
	@$(TASK) dist:linux

dist-linux-x64:
	@$(TASK) dist:linux-x64

help:
	@echo "Makefile targets delegate to Task (see: task --list)."
	@$(TASK) --list
