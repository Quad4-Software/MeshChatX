# Frontend conventions

Applies when editing `meshchatx/src/frontend/**/*.{js,ts,svelte}`.

- Live UI is Svelte 5 (runes). Boot is `main.ts` -> `features/app-shell/App.svelte` + `shell/hashRouter.ts` + `shell/PageOutlet.svelte`.
- Do not add Vue SFCs, vue-router, vue-i18n, or Vue test-utils.
- Feature modules, `ui/svelte/`, and the `js/` kernel use TypeScript (`.ts`, `lang="ts"` in `.svelte`). Do not grow new plain `.js` under `js/` or `features/`.
- New routes use `registerFeature` / `routeRegistry` with `mount: "svelte"`. Do not hardcode routes in `main.ts`.
- i18n is `svelte-i18n` via `js/localeLoader.ts` (`initSvelteI18n`, `setLocale`). Pages use `t()` from `js/i18n.ts`.
- API calls go through `window.api` (not ad-hoc axios imports in pages).
- Toasts: `ToastUtils.success|error|warning|info|loading|dismiss`.
- New top-level pages need: feature registration, nav entry when discoverable, `en.json` keys, frontend tests.
- When adding user-visible strings, update `en.json` and the other maintained locale files under `meshchatx/src/frontend/locales/` with real translations (not English copies).
- Sidebar unread pills live on nav entries in `coreNavEntries.js` and counters in `GlobalState`. Do not bring back a header notification bell for that job.
- Identity-scoped persistence: localStorage state that belongs to an identity (drafts, ignore lists, per-room prefs) must be bucketed under the identity hash, and the identity key must be captured when the state is loaded, never re-read from the config store at save time. A deferred save (on room switch, route leave, unmount, or identity switch) that resolves the live identity can write one identity's data into another's bucket. `js/identityScope.js` (`useIdentityScope`) is the canonical primitive: `beginIdentity` captures the identity at load time and `keyForWrite` resolves saves against the captured key. `features/messages/lib/conversationDrafts.ts` shows the same capture rule applied to compose drafts. Any new per-identity store must use the scope (or the same capture rule) plus a regression test that switches identity between load and save.
- File inputs: prefer broad `accept` for identity keys (`.bin,.key,.identity,application/octet-stream,*/*`). Database restore stays `.zip`.
- Prefer existing MaterialDesignIcon / layout patterns over new design systems.
- No backticks in code comments. Prefer plain words or quoted identifiers.

## Layers

| Layer    | Location                                                    | May import                     |
| -------- | ----------------------------------------------------------- | ------------------------------ |
| Kernel   | `js/` (api, registries, toast, theme, state, i18n) as `.ts` | other kernel only              |
| UI       | `ui/svelte/`                                                | kernel                         |
| Features | `features/<id>/`                                            | kernel, ui, own files          |
| Shell    | `features/app-shell/`, `shell/`, boot (`main.ts`)           | kernel, registries, PageOutlet |

Cross-feature UI imports are forbidden. Share through kernel events, registries, or `ui/`.

## Svelte

- `pnpm run svelte-check` and `pnpm run format:check:svelte` in `task lint:frontend`. Runes mode only.
- Prefer small `features/<id>/components/` and `lib/` pieces. Do not grow Svelte god pages.
- Feature `lib/` and `index` files are TypeScript. Svelte scripts use `lang="ts"`.
- Host flip gate: `tests/frontend/hostFlipReadiness.test.js` and `tests/frontend/svelteShellMigrationRegressions.test.js`.
- Skill: `.agents/skills/svelte-feature-modules/SKILL.md`.

## Shared UI primitives

Prefer these over ad-hoc gray/blue utilities on new or touched surfaces:

- Semantic tokens (`sem-*`) from the theme engine
- `ui/svelte/` Modal, Toast, ConfirmDialog, MaterialDesignIcon, SettingToggleRow patterns
- Feature-local panels under `features/<id>/components/`
