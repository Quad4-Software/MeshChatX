---
name: contribution-registries
description: Nav, tools, commands, settings search, and WS events through registries. Use when adding a discoverable page, command, settings section, or WS handler.
---

# Skill: contribution-registries

Wire nav, tools, commands, settings search, and WebSocket events through registries instead of hardcoding shell or App.vue dispatch.

## When to use

- Adding a discoverable page, tool, command palette entry, or settings section
- Adding a new WebSocket event type handled by the UI
- Plugin contribution points or slot UI
- Adding or changing a sidebar nav badge (unread counts)

## Registries

| Registry                                  | Role                                  |
| ----------------------------------------- | ------------------------------------- |
| navRegistry.js                          | Primary sidebar / nav                 |
| toolsRegistry.js                        | Tools area entries                    |
| commandRegistry.js                      | Command palette                       |
| settingsSectionRegistry.js              | Settings search / sections            |
| wsEventRegistry.js + wsEventBridge.js | Typed WS handlers                     |
| postInstallPromptRegistry.js            | Existing-user / after-install prompts |
| routeRegistry.js + featureRegistry.js | Feature routes (registerFeature)    |
| features/registerAllFeatures.js         | Boot hook for feature modules         |

Core boot registers once via registerCoreContributions.js and core*Entries.js siblings.
Feature modules register via features/registerAllFeatures.js (see features/<id>/ and svelte-feature-modules skill).
Shell builds registry routes with shell/buildRouterRoutes.js. Do not add new routes to the hardcoded table in main.js.

## Nav badges

Sidebar pills are declared on CORE_NAV_ENTRIES in coreNavEntries.js via badge: { source, pill, cap }.

Current sources:

| Source                     | Meaning                                     | Cleared when                         |
| -------------------------- | ------------------------------------------- | ------------------------------------ |
| unreadConversationsCount | Unread LXMF conversations                   | Conversation marked read             |
| relayChatUnreadCount     | RRC mention count (when relay chat enabled) | Mentions consumed on Relay chat page |
| missedCallsCount         | Unviewed telephone_missed_call rows       | Call page opened or history cleared  |

App.vue maps each source through GlobalState and getNavBadgeCount. Collapsed sidebar still shows pill badges on the icon. There is no header notification bell anymore. Message sounds stay under Settings.

For a new badge:

1. Add a GlobalState counter
2. Add a NavBadgeSource value and badge on the nav entry
3. Wire getNavBadgeCount in features/app-shell/ (GlobalState-backed)
4. Refresh the count from the right API or WebSocket event
5. Clear it when the user has actually seen the related UI

## Post-install / existing-user prompts

Use postInstallPromptRegistry + PostInstallPromptHost when you need to ask existing installs to do or acknowledge something after an upgrade.

1. Add an entry to corePostInstallPromptEntries.js with a stable id, revision, and i18n titleKey (optional description and button keys).
2. Register happens via registerCoreContributions.
3. App.vue shows the next pending prompt after tutorial / Android storage upgrade and before changelog.
4. To show the same prompt again later, bump revision. Users who dismissed an older revision are prompted again.
5. Optional shouldShow() gates platform or feature conditions. Optional onPrimary / onSecondary run actions before dismiss.

Seen revisions live in localStorage under meshchatx.post_install_prompts_seen via postInstallPromptState.js.

## Hard rules

- New top-level pages still need a route in main.js (see page-toast-tests). Registries cover discoverability and dispatch, not routing alone.
- Prefer onWsEvent / registry handlers over growing ad-hoc switch (json.type) blocks in App.vue.
- Settings search keywords belong in the settings section registry, not scattered only inside SettingsPage.svelte.
- Plugin UI uses the existing slot vocabulary (PluginSlotNode / related renderers). Extend that vocabulary in place. Do not invent a parallel slot system. Document new node types in docs/en/plugins.md and validate them in pluginUiDescriptor.js.

## Key files

- meshchatx/src/frontend/js/registries/
- meshchatx/src/frontend/js/registries/registerCoreContributions.js
- meshchatx/src/frontend/js/registries/coreNavEntries.js
- meshchatx/src/frontend/js/GlobalState.js
- meshchatx/src/frontend/components/plugins/PluginSlotNode.vue
- meshchatx/src/frontend/main.js (routes)

## Verification

```bash
pnpm exec vitest run tests/frontend/ -t registry
```

If no dedicated registry tests match, run the page or App tests that cover the new entry, plus eslint on touched files.
