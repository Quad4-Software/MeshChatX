---
name: page-toast-tests
description: New MeshChatX pages with routes, nav, toasts, i18n, and tests. Use when adding a page or wiring ToastUtils and locale keys.
---

# Skill: page-toast-tests

New MeshChatX pages with routes, nav, toasts, i18n, and tests.

# MeshChatX Page + Toast + Tests

## Purpose

Use this skill to implement feature pages in this repository without missing integration points:

- frontend route registration
- navigation exposure
- translated labels
- user feedback via ToastUtils
- test coverage updates

This skill is optimized for the MeshChatX structure under meshchatx/src/frontend and tests/.

## Quick Decisions

Before editing files, decide:

1. Is this a top-level page route or a modal/section inside an existing page?
2. Does the action require backend API work, or can it stay frontend-only?
3. Which toast types are expected on success, warning, and failure?
4. Which tests should prove behavior: frontend unit test, backend test, or both?

## Required Integration Points

For a new top-level page, verify all relevant items:

- Prefer features/<id>/ + registerFeature (see svelte-feature-modules skill). Wire via features/registerAllFeatures.ts. Do not grow hardcoded routes in main.ts.
- Greenfield UI: Svelte 5 under features/<id>/ or ui/svelte/.
- Add sidebar/tools entry through nav/tools registries when the page must be user-discoverable.
- Add translation keys in meshchatx/src/frontend/locales/en.json and other maintained locale files when touched by task scope.
- Use ToastUtils in page actions that save, submit, refresh, copy, or fail.
- Add or update tests in tests/frontend/*.test.js.
- Add or update backend tests in tests/backend/*.py if API behavior changes.

## Page Creation Workflow

### 1) Create the page component

Place the component in the matching feature directory, for example:

- meshchatx/src/frontend/features/<id>/<NewPage>.svelte
- meshchatx/src/frontend/features/<id>/components/<NewPage>.svelte

Keep the page consistent with existing patterns:

- use translated UI text with t("...") from js/i18n.ts
- use window.api for API calls in page logic
- use MaterialDesignIcon patterns already used in peer pages

### 2) Register route

In features/<id>/index.ts via registerFeature:

- add a route with stable name, path, mount: "svelte", and load()
- call the register from features/registerAllFeatures.ts
- pass route params through the page props contract when needed

### 3) Surface navigation

If user navigation should expose the page:

- add a navRegistry entry (coreNavEntries or feature register), or
- add it in toolsRegistry if it belongs under tools, not primary nav

Keep naming consistent between route name, i18n label, and visible button/link text.

## Toast Conventions

Import from:

- meshchatx/src/frontend/js/ToastUtils.js

Use:

- ToastUtils.success(message) for completion
- ToastUtils.error(message) for failures
- ToastUtils.warning(message) for recoverable risk
- ToastUtils.info(message) for neutral updates
- ToastUtils.loading(message, 0, key) and ToastUtils.dismiss(key) for long-running operations

Guidelines:

- prefer translated messages from locale keys over hardcoded strings
- include backend-provided error detail when safe and useful
- for progress toasts, use stable keys to avoid stacking duplicates

## Test Workflow

### Frontend tests (vitest)

When adding page behavior:

- create or extend a test in tests/frontend/
- render or exercise the page/helpers with locale and router mocks as nearby tests do
- stub non-essential child components when mounting UI
- mock window.api responses for success and error flows
- assert both state and rendered output
- assert toast calls when operation outcomes are user-visible

### Backend tests (pytest)

When API/backend behavior is changed:

- add focused tests under tests/backend/
- patch heavy dependencies and network side effects
- verify returned payload shape and error contracts expected by frontend
- keep fixture setup minimal and local to behavior under test

## Done Checklist

Only finish once these are true:

- route works and page renders from navigation path
- all user-facing strings are translated keys
- toast behavior exists for core success/failure actions
- frontend test covers key path and an error path
- backend tests are updated if API behavior changed
- no unrelated files were changed

## Quality Bar

- Follow existing file and naming conventions before introducing new patterns.
- Keep implementation incremental. Avoid broad refactors in feature delivery.
- Prefer clear user feedback over silent failures.
- Match current test style in nearby files instead of inventing a new structure.

## Additional Resources

- Trigger and output examples: [examples.md](examples.md)
- Feature modules: .agents/skills/svelte-feature-modules/SKILL.md
