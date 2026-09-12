---
name: vue-mega-page-split
description: Extract Vue mega-page shells into internal/sections/helpers without behaviour change. Use when splitting listed mega-pages from module-ownership.md.
---

# Skill: vue-mega-page-split

Extract or split Vue mega-page shells under `meshchatx/src/frontend/components/`
without changing behaviour.

## When to use

- Splitting listed mega-pages from `.agents/module-ownership.md`
- Moving presentational panels into `internal/` or `settings/sections/`
- Extracting pure helpers next to a page or under `js/<feature>/`

Not for greenfield pages. Use `page-toast-tests` for new routes and nav wiring.

Also read:

- `.agents/module-ownership.md` (Frontend mega-pages)
- `.agents/conventions/frontend.md`
- `.agents/conventions/tests.md`
- `.agents/skills/test-loop/SKILL.md`

## Hard rules

1. Mechanical extract only. No renames, no toast or i18n churn, no API path changes in the same change as a move.
2. One concern per change: move or behaviour, never both.
3. Mechanical extracts keep the parent's Options API style so the diff stays a pure move. Outside a mechanical move — new components, new stores, behaviour changes — Composition API (`<script setup>`), composables, provide/inject, and Pinia (`js/stores/`) are allowed and preferred for new code.
4. Follow inventory names in `.agents/module-ownership.md`. Do not invent alternate folders.
5. Shell stays orchestration. Data ownership, `window.api`, map or canvas lifecycle init and teardown, and multi-child toast firing stay on the page shell unless a later behaviour change explicitly moves them.
6. One slice per PR or commit series. Prefer one panel, one settings section, or one pure helper module.
7. Promote to shared root components only when two or more unrelated features need the same UI.
8. Keep SPDX on new project files (`0BSD` unless the file already differs).
9. Do not edit locale files in a mechanical extract.

## Placement

Placement table (page-private panels, settings chunks, pure logic, cross-feature primitives, nav/tools wiring): `.agents/module-ownership.md` (Frontend mega-pages section). Do not invent folders outside that table.

## Pre-extract inventory (mandatory)

Before editing, list:

- Method, computed, and data keys touched by the slice
- Template markers (`$t` keys, `ref=` names, handler names, `v-if` flags)
- `/api/v1/...` path fragments and `window.api` usages in the slice
- External imports the slice needs
- Existing tests that mount the parent or assert those strings

Inventing symbols not in the inventory is a fail.

## Cut order inside a shell

1. Pure JS first (no `this`, no template). Unit-test like `MapInternalHelpers.test.js`.
2. Composables next for stateful feature slices (`js/<feature>/useX.js`). See "Composable extraction" below.
3. Presentational panels next (props in, events out). Match `settings/sections/`.
4. Stateful feature chunks last. Keep Leaflet, WebGL, and WS lifecycle on the shell until the boundary is obvious.

## Composable extraction

A composable slice moves a self-contained feature concern (its refs, computed,
watchers, and plain functions) out of an Options API shell into
`js/<feature>/useSomething.js`, while the host stays Options API.

Host wiring:

```js
setup() {
    return { ...useConversationSearch() };
},
```

Refs and functions returned from `setup()` merge onto `this`, so the template
and untouched options keep working. Only move a coherent cluster: the
`data` keys, `computed`, `watch` entries, and `methods` that reference each
other and nothing else.

Hard constraints:

- Never move a symbol that tests call bare on the options object
  (`Component.methods.X()`, `Component.computed.X()`, `Component.data()`).
  Either keep a thin delegating method on the host, or leave the symbol.
- `this.$route`, `this.$router`, `this.$t` are instance-only: pass them in as
  parameters or keep the calling method on the host.
- Lifecycle hooks may live inside the composable (`onMounted`, `onUnmounted`)
  but only when the moved cluster owns that lifecycle fully.
- Names starting with `_` must not be returned from `setup()` — Vue treats them
  as reserved and warns. Either keep those methods on the host, or expose them
  through an options callback the host delegates to.
- Composables get their own unit tests under `tests/frontend/`; the host's
  tests must stay untouched and green.

## Vue cut recipe

1. Identify a contiguous template region plus its methods, computed, and data.
2. Create the child with SPDX header, Options API, props and emits only for the boundary.
3. Move markup and methods verbatim. Keep names.
4. Wire parent import, `components`, and thin wrappers if parent tests still call old method names.
5. Add or adjust focused tests for the child. Keep parent smoke tests green.
6. Run continuity checks and focused vitest.

## Size budgets

- Prefer extracting when a contiguous concern is about 150 to 300 lines or a whole settings section.
- Aim shells toward under about 2000 lines across multiple PRs.
- Stop a PR when the review diff exceeds roughly one concern (about 300 to 800 lines moved).

## Diff continuity checklist

After the move:

1. `git diff --stat` shows LOC moved, not vanished.
2. Every inventory method name still hits under the feature tree.
3. Every inventory `$t` key still exists under the feature tree.
4. No route, nav, or registry edits unless the slice explicitly required them.
5. No locale file edits.
6. Parent registers new children. Template uses them. Old inline markup is removed only for the sliced region.

## Hallucination tripwires (stop-ship)

- New public methods or renamed handlers for cleanliness
- Switching an existing component from Options API to Composition API inside a mechanical extract
- Child calling `window.api` when the parent previously owned that call, unless the inventory moved the whole call site and tests cover it
- Deleted emits, props, or refs that tests or the parent still need
- Folders not listed in ownership
- Hardcoded English replacing `$t(...)`
- Updating ownership fixtures only to make a red test green

## Contract scanners

Fixtures:

- `tests/frontend/fixtures/frontend_mega_page_ownership.json`
- `tests/frontend/fixtures/frontend_symbol_continuity/<page>.json`

Tests:

- `tests/frontend/frontendOwnershipContract.test.js`
- helpers under `tests/frontend/helpers/`

Refresh ownership fixture only when inventory intentionally changes:

```bash
UPDATE_FRONTEND_OWNERSHIP=1 pnpm exec vitest run tests/frontend/frontendOwnershipContract.test.js -t ownership_fixture
```

## Verification

Per slice:

```bash
pnpm exec eslint <touched files> --fix
pnpm exec vitest run tests/frontend/<Parent>*.test.js \
  tests/frontend/<SliceOrHelper>*.test.js \
  tests/frontend/frontendOwnershipContract.test.js \
  tests/frontend/behaviorContracts.test.js
```

Per milestone (meaningful shell shrink or before merge):

```bash
task test:frontend
```

Do not treat `task test:quick` alone as sufficient for map, settings, call, or conversation extracts.
`task test:quick:fe` includes `frontendOwnershipContract.test.js` as a gate, not full page coverage.

## Workflow card

1. Read this skill and the ownership row for the page.
2. Build the pre-extract inventory.
3. Mechanical move only into an allowed directory.
4. Continuity `rg` plus ownership contract tests.
5. Focused vitest for parent, new files, and `behaviorContracts`.
6. Eslint on touched files.
7. Milestone: `task test:frontend`.
