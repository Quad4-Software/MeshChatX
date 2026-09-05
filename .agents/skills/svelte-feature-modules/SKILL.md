---
name: svelte-feature-modules
description: Svelte 5 pages and feature modules for MeshChatX. Use when adding Svelte UI, registerFeature routes, or dual Vue/Svelte mounts.
---

# Skill: svelte-feature-modules

Gradual Vue to Svelte 5 migration with pluggable feature modules.

## When to use

- New greenfield pages or shared UI
- Moving a route behind `registerFeature`
- Writing `.svelte` / `.svelte.js` code
- Dual-stack mount (`vue` or `svelte`)

## Hard rules

1. Svelte 5 runes only (`compilerOptions.runes: true`). No legacy `export let`.
2. New routes go through `registerFeature` / `routeRegistry`. Do not grow the hardcoded table in `main.js`.
3. API via `window.api` / kernel clients. Toasts via `ToastUtils`.
4. User-visible strings: locale JSON + `t()` from kernel i18n adapter (or Vue `$t` in remaining Vue).
5. Import boundaries: `js/` kernel must not import `components/`, `features/`, or `.svelte`/`.vue`. Features may import kernel and `ui/`.
6. Prefer `ui/svelte/` for shared primitives. Prefer `features/<id>/` for page ownership.
7. Mount bridge uses Svelte `mount` / `unmount` into a Vue host. No custom-element shadow DOM for in-app pages.
8. One feature or primitive per PR series. No god-file rewrites.
9. SPDX on new project files (`0BSD` unless the file already differs).
10. Run `pnpm run svelte-check` for touched Svelte surfaces.

## Layout

```
meshchatx/src/frontend/
  ui/svelte/           shared primitives
  features/<id>/       register + page + lib
  js/registries/       routeRegistry, registerFeature, existing nav/tools/...
  components/          legacy Vue (shrink)
  shell/               optional future host (Vue App.vue is shell today)
```

## Register a feature

```js
import { registerFeature } from "../../js/registries/featureRegistry.js";

export function registerBlockedFeature() {
    registerFeature({
        id: "blocked",
        routes: [
            {
                name: "blocked",
                path: "/blocked",
                mount: "svelte",
                load: () => import("./BlockedPage.svelte"),
            },
        ],
    });
}
```

Call registers from `features/registerAllFeatures.js` at boot after `registerCoreContributions`.

## Checks

```bash
pnpm run svelte-check
pnpm exec vitest run tests/frontend/<Name>.svelte.test.js
pnpm exec vitest run tests/frontend/featureRouteRegistry.test.js
```
