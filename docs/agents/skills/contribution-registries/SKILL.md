# Skill: contribution-registries

Wire nav, tools, commands, settings search, and WebSocket events through registries instead of hardcoding shell or App.vue dispatch.

## When to use

- Adding a discoverable page, tool, command palette entry, or settings section
- Adding a new WebSocket event type handled by the UI
- Plugin contribution points or slot UI

## Registries

| Registry                                  | Role                       |
| ----------------------------------------- | -------------------------- |
| `navRegistry.js`                          | Primary sidebar / nav      |
| `toolsRegistry.js`                        | Tools area entries         |
| `commandRegistry.js`                      | Command palette            |
| `settingsSectionRegistry.js`              | Settings search / sections |
| `wsEventRegistry.js` + `wsEventBridge.js` | Typed WS handlers          |

Core boot registers once via `registerCoreContributions.js` and `core*Entries.js` siblings.

## Hard rules

- New top-level pages still need a route in `main.js` (see `page-toast-tests`). Registries cover discoverability and dispatch, not routing alone.
- Prefer `onWsEvent` / registry handlers over growing ad-hoc `switch (json.type)` blocks in `App.vue`.
- Settings search keywords belong in the settings section registry, not scattered only inside `SettingsPage.vue`.
- Plugin UI uses the existing slot vocabulary (`PluginSlotNode` / related renderers). Do not invent a parallel slot system.

## Key files

- `meshchatx/src/frontend/js/registries/`
- `meshchatx/src/frontend/js/registries/registerCoreContributions.js`
- `meshchatx/src/frontend/components/plugins/PluginSlotNode.vue`
- `meshchatx/src/frontend/main.js` (routes)

## Verification

```bash
pnpm exec vitest run tests/frontend/ -t registry
```

If no dedicated registry tests match, run the page or App tests that cover the new entry, plus eslint on touched files.
