# Frontend conventions

Applies when editing `meshchatx/src/frontend/**/*.{vue,js,ts,svelte}`.

- Vue 3 Options API remains the pattern for existing `.vue` files. Match the file you edit.
- New greenfield pages and shared UI go Svelte 5 (runes only) under `ui/svelte/` or `features/<id>/`.
- Feature modules, `ui/svelte/`, and the `js/` kernel use TypeScript (`.ts`, `lang="ts"` in `.svelte`). Keep `allowJs` only for remaining Vue SFC scripts and third-party bits. Do not grow new plain `.js` under `js/` or `features/`.
- New routes use `registerFeature` / `routeRegistry`. Do not add one-off routes to the hardcoded table in `main.js`.
- API calls go through `window.api` (not ad-hoc axios imports in pages).
- Toasts: `ToastUtils.success|error|warning|info|loading|dismiss`.
- New top-level pages need: feature registration (or legacy route until absorbed), nav entry when discoverable, `en.json` keys, frontend tests.
- When adding user-visible strings, update `en.json` and the other maintained locale files under `meshchatx/src/frontend/locales/` with real translations (not English copies).
- Sidebar unread pills live on nav entries in `coreNavEntries.js` and counters in `GlobalState`. Do not bring back a header notification bell for that job.
- Do not use `_`-prefixed keys in Vue `data()` (`vue/no-reserved-keys`).
- File inputs: prefer broad `accept` for identity keys (`.bin,.key,.identity,application/octet-stream,*/*`). Database restore stays `.zip`.
- Prefer existing MaterialDesignIcon / layout patterns over new design systems.
- No backticks in code comments. Prefer plain words or quoted identifiers.

## Layers

| Layer    | Location                                           | May import                          |
| -------- | -------------------------------------------------- | ----------------------------------- |
| Kernel   | `js/` (api, registries, toast, theme, state, i18n) as `.ts` | other kernel only                   |
| UI       | `ui/svelte/`, shared Vue primitives                | kernel                              |
| Features | `features/<id>/`                                   | kernel, ui, own files               |
| Shell    | `App.vue`, boot (`main.js`)                        | kernel, registries, page mount host |

Cross-feature UI imports are forbidden. Share through kernel events, registries, or `ui/`.

## Conveyor (Vue to Svelte)

1. Absorb a quiet leaf into `features/<id>/` with `registerFeature` (Vue mount first is fine).
2. Extract pure helpers under `features/<id>/lib/`.
3. Rewrite the page to Svelte, set `mount: "svelte"`.
4. Keep a thin Vue wrapper only while tests or imports still need it.
5. Update `FEATURE_MODULE_OWNERS` in `tests/frontend/featureModuleOwnership.test.js`.
6. Host flip (`App.vue` to Svelte shell) waits until registry routes no longer need `mount: "vue"` and legacy hardcoded routes are gone. See `tests/frontend/hostFlipReadiness.test.js`.

## Svelte

- `pnpm run svelte-check` and `pnpm run format:check:svelte` in `task lint:frontend`. Runes mode only.
- Prefer small `features/<id>/components/` and `lib/` pieces. Do not grow Svelte god pages.
- Feature `lib/` and `index` files are TypeScript. Svelte scripts use `lang="ts"`.
- Dual mount: route meta `mount: "vue" | "svelte"` with a lazy `load`.
- Skill: `.agents/skills/svelte-feature-modules/SKILL.md`.

## Shared UI primitives

Prefer these over ad-hoc gray/blue utilities on new or touched surfaces:

- `EmptyState`, `LoadingState`, `Skeleton` for empty / loading / placeholder rows
- `IconButton` for icon-only controls (includes `focus-ring-sem` and 44px touch target)
- CSS helpers in `style.css`: `input-field`, `primary-chip` / `secondary-chip` / `danger-chip`, `focus-ring-sem`, `press-feedback`, `page-canvas`
- Focus rings: `focus-ring-sem` or `focus:ring-sem-focus`, not `focus:ring-blue-500`
- Primary actions: `primary-chip` or `bg-sem-action-primary`, not raw `bg-blue-600`
- Honor `prefers-reduced-motion` on new animation (route fade and chip press already do)

## Mega-page extracts

When splitting large Vue page shells, follow `.agents/skills/vue-mega-page-split/SKILL.md`
and the Frontend mega-pages table in `.agents/module-ownership.md`.

- Mechanical extract only. Move or behaviour change, never both in the same change.
- Prefer `internal/` or `settings/sections/` for page-private UI. Prefer colocated or `js/<feature>/` for pure helpers.
- Aim shells toward under about 2000 lines across multiple PRs. Prefer slices of about 150 to 300 lines.
- Verify with ownership contracts in `tests/frontend/frontendOwnershipContract.test.js` plus focused page tests.
- Do not treat `task test:quick` alone as enough coverage for map, settings, call, or conversation extracts.
