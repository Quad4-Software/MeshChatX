# Frontend conventions

Applies when editing `meshchatx/src/frontend/**/*.{vue,js}`.

- Vue 3 Options API is the dominant pattern. Match the file you edit.
- API calls go through `window.api` (not ad-hoc axios imports in pages).
- Toasts: `ToastUtils.success|error|warning|info|loading|dismiss`.
- New top-level pages need: route in `main.js`, nav entry when discoverable, `en.json` keys, frontend tests.
- Sidebar unread pills live on nav entries in `coreNavEntries.js` and counters in `GlobalState`. Do not bring back a header notification bell for that job.
- Do not use `_`-prefixed keys in Vue `data()` (`vue/no-reserved-keys`).
- File inputs: prefer broad `accept` for identity keys (`.bin,.key,.identity,application/octet-stream,*/*`). Database restore stays `.zip`.
- Prefer existing MaterialDesignIcon / layout patterns over new design systems.
