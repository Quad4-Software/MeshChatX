# Frontend conventions

Applies when editing `meshchatx/src/frontend/**/*.{vue,js}`.

- Vue 3 Options API is the dominant pattern. Match the file you edit.
- API calls go through `window.api` (not ad-hoc axios imports in pages).
- Toasts: `ToastUtils.success|error|warning|info|loading|dismiss`.
- New top-level pages need: route in `main.js`, nav entry when discoverable, `en.json` keys, frontend tests.
- When adding user-visible strings, update `en.json` and the other maintained locale files under `meshchatx/src/frontend/locales/` with real translations (not English copies).
- Sidebar unread pills live on nav entries in `coreNavEntries.js` and counters in `GlobalState`. Do not bring back a header notification bell for that job.
- Do not use `_`-prefixed keys in Vue `data()` (`vue/no-reserved-keys`).
- File inputs: prefer broad `accept` for identity keys (`.bin,.key,.identity,application/octet-stream,*/*`). Database restore stays `.zip`.
- Prefer existing MaterialDesignIcon / layout patterns over new design systems.
- No backticks in code comments. Prefer plain words or quoted identifiers.

## Shared UI primitives

Prefer these over ad-hoc gray/blue utilities on new or touched surfaces:

- `EmptyState`, `LoadingState`, `Skeleton` for empty / loading / placeholder rows
- `IconButton` for icon-only controls (includes `focus-ring-sem` and 44px touch target)
- CSS helpers in `style.css`: `input-field`, `primary-chip` / `secondary-chip` / `danger-chip`, `focus-ring-sem`, `press-feedback`, `page-canvas`
- Focus rings: `focus-ring-sem` or `focus:ring-sem-focus`, not `focus:ring-blue-500`
- Primary actions: `primary-chip` or `bg-sem-action-primary`, not raw `bg-blue-600`
- Honor `prefers-reduced-motion` on new animation (route fade and chip press already do)

## Mega-page extracts

When splitting large page shells, follow `.agents/skills/vue-mega-page-split/SKILL.md`
and the Frontend mega-pages table in `.agents/module-ownership.md`.

- Mechanical extract only. Move or behaviour change, never both in the same change.
- Prefer `internal/` or `settings/sections/` for page-private UI. Prefer colocated or `js/<feature>/` for pure helpers.
- Aim shells toward under about 2000 lines across multiple PRs. Prefer slices of about 150 to 300 lines.
- Verify with ownership contracts in `tests/frontend/frontendOwnershipContract.test.js` plus focused page tests.
- Do not treat `task test:quick` alone as enough coverage for map, settings, call, or conversation extracts.
