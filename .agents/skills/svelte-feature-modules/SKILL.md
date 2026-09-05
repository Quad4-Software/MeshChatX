---
name: svelte-feature-modules
description: Svelte 5 pages and feature modules for MeshChatX. Use when adding Svelte UI or registerFeature routes.
---

# Skill: svelte-feature-modules

Svelte 5 runes feature modules behind `registerFeature` and the hash router shell.

## When to use

- New greenfield pages or shared UI
- Moving a route behind `registerFeature`
- Writing `.svelte` / `.svelte.ts` code

## Hard rules

1. Svelte 5 runes only (`compilerOptions.runes: true`). No legacy `export let`.
2. New routes go through `registerFeature` / `routeRegistry` with `mount: "svelte"`. Do not grow hardcoded routes in `main.ts`.
3. API via `window.api` / kernel clients. Toasts via `ToastUtils`.
4. User-visible strings: locale JSON + `t()` from `js/i18n.ts` (svelte-i18n via `localeLoader.ts`).
5. Import boundaries: `js/` kernel must not import `components/`, `features/`, or `.svelte`. Features may import kernel and `ui/`.
6. Prefer `ui/svelte/` for shared primitives. Prefer `features/<id>/` for page ownership.
7. Pages mount through `shell/PageOutlet.svelte` and `shell/hashRouter.ts`.
8. One feature or primitive per PR series. No god-file rewrites.
9. SPDX on new project files (`0BSD` unless the file already differs).
10. Run `pnpm run svelte-check` for touched Svelte surfaces.
11. Feature modules, `ui/svelte/`, and the `js/` kernel use TypeScript: `index.ts`, `lib/*.ts`, kernel `.ts`, and `<script lang="ts">` in `.svelte`.

## Layout

```
meshchatx/src/frontend/
  ui/svelte/                 shared primitives
  features/<id>/             register + page + lib
  features/app-shell/        live App.svelte shell
  js/registries/             routeRegistry, registerFeature, nav/tools/...
  shell/                     hashRouter, PageOutlet
  components/                leftover Vue (do not grow)
```

## Register a feature

```ts
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

Call registers from `features/registerAllFeatures.ts` at boot after `registerCoreContributions`.

## Checks

```bash
pnpm run svelte-check
pnpm run format:check:svelte
pnpm exec vitest run tests/frontend/<Name>.test.js
pnpm exec vitest run tests/frontend/featureModuleOwnership.test.js
```
