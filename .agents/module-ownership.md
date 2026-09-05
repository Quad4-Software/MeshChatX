# Module ownership map

Domain ownership for MeshChatX. Use this when deciding where code and tests live.
Orchestration entry remains `meshchatx.meshchat` (`ReticulumMeshChat`, `main`).

Schema contracts live under `tests/backend/` (not production route modules).

## Backend

| Domain            | Manager modules                                                   | HTTP route module                           | WS module                    | Primary tests                                                                              | Frontend page                                                                   |
| ----------------- | ----------------------------------------------------------------- | ------------------------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------- |
| Identity          | `identity_context.py`, `identity_manager.py`                      | `http/routes/identities.py`                 | `http/ws/dispatch.py`        | `test_identity_*`, identity-switch skills                                                  | Identities / tutorial                                                           |
| Status / startup  | `lifecycle/deferred_network.py`, `rns_startup_recovery.py`        | `http/routes/status.py`                     | (status via REST)            | `test_deferred_network_startup.py`, `test_api_json_contracts.py`                           | App shell banners                                                               |
| Auth / CSRF       | `csrf.py`, `app_security_settings.py`, `ip_allowlist.py`          | `http/routes/auth.py`                       | `http/ws/dispatch.py`        | `test_csrf*`, `test_access_attempts_*`                                                     | Auth gate in `App.vue`                                                          |
| Messages / LXMF   | `message_handler.py`, `lxmf_utils.py`, `database/messages.py`     | `http/routes/messages.py`, `lxmf.py`        | `http/ws/dispatch.py`        | LXMF messaging skill tests                                                                 | `features/messages/MessagesPage.svelte`, `components/ConversationViewer.svelte` |
| Telephone / LXST  | `telephone_manager.py`, `database/telephone.py`                   | `http/routes/telephone.py`, `contacts.py`   | `http/ws/dispatch.py`        | telephone contract tests                                                                   | `call/CallPage.vue`                                                             |
| RRC               | `rrc/manager.py`, `rrc/server.py`                                 | `http/routes/rrc.py`                        | `http/ws/dispatch.py`        | RRC skill tests                                                                            | `relay/RelayChatPage.vue`                                                       |
| Map               | `map_manager.py`, `map_overlay_manager.py`, `map_data_manager.py` | `http/routes/map.py`                        | marker updates via broadcast | map manager tests                                                                          | `map/MapPage.vue`                                                               |
| Plugins           | `plugin_manager.py`, `plugin_permissions.py`                      | `http/routes/plugins.py`, `sideband.py`     | `http/ws/dispatch.py`        | plugin install security tests                                                              | `settings/PluginsSettingsSection.vue`                                           |
| FileSync          | `rns_filesync_handler.py`                                         | `http/routes/filesync.py`                   | (REST-heavy)                 | filesync security tests                                                                    | `filesync/` pages                                                               |
| Interfaces        | `interface_editor.py`, `interface_config_parser.py`               | `http/routes/interfaces.py`                 | (announce loops on app)      | interface stats tests                                                                      | `interfaces/InterfacesPage.vue`                                                 |
| Database / backup | `database/*`, `recovery/*`                                        | `http/routes/database.py`, `maintenance.py` | (broadcasts on restore)      | backup/restore skill tests                                                                 | About / maintenance settings                                                    |
| Docs              | `docs_manager.py`                                                 | `http/routes/docs.py`                       | (none)                       | docs manager tests                                                                         | `docs/DocsPage.vue`                                                             |
| Sandbox           | `landlock_sandbox.py`, `seccomp_sandbox.py`                       | `http/routes/status.py`                     | (none)                       | `test_landlock_sandbox.py`, `test_landlock_integration_surfaces.py`, sqlite landlock tests | Web exposure settings                                                           |
| RNS Link API      | `rns_link_manager.py`                                             | (WS only)                                   | `http/ws/dispatch.py`        | `test_rns_link_*`                                                                          | plugins / external tools                                                        |
| Config            | `config_manager.py`                                               | `http/routes/config.py`                     | `http/ws/dispatch.py`        | settings config services tests                                                             | `settings/SettingsPage.vue`                                                     |

## HTTP package layout

```
meshchatx/src/backend/http/
  context.py
  errors.py
  live_names.py
  middleware.py
  register.py
  routes/<domain>.py
  routes/__init__.py
  ws/dispatch.py
```

`register_all_routes(routes, app)` is the sole composition entry. Call it only from
`ReticulumMeshChat._define_routes`. Domain register functions are listed in fixed order
in `routes/__init__.py`. Free names resolve through `live_names.inject_meshchat_names`.

WS inbound handlers live in `ws/handlers_*.py` and are composed by `ws/dispatch.py`.

## Frontend mega-pages

Placement for extracts. Follow `.agents/skills/vue-mega-page-split/SKILL.md`.
Do not invent folders outside this table.

| Kind                            | Put it here                                               | Example                             |
| ------------------------------- | --------------------------------------------------------- | ----------------------------------- |
| Page-private panel or UI        | `components/<feature>/internal/*.vue`                     | MapSearchBar                        |
| Settings chunk                  | `components/settings/sections/*SettingsSection.vue`       | TelephonySettingsSection            |
| Pure logic                      | colocated `*.js` or `js/<feature>/`                       | clusterUtils, settingsConfigService |
| Cross-feature primitive         | root `components/` or `components/forms/` or `ui/svelte/` | ConfirmDialog, Toggle               |
| Feature module (new / migrated) | `features/<id>/` (page + `index.js` register)             | `features/blocked/`                 |
| Nav, tools, commands, routes    | `js/registries/` only                                     | never grow App.vue / main.js tables |
| Shell chrome / page host        | `shell/`                                                  | FeaturePageHost, buildRouterRoutes  |

| Page shell                                               | On-disk child dirs                                                   | Planned child dirs                           | Shared JS                           | Primary tests                                                                    |
| -------------------------------------------------------- | -------------------------------------------------------------------- | -------------------------------------------- | ----------------------------------- | -------------------------------------------------------------------------------- |
| `settings/SettingsPage.vue`                              | `settings/sections/` (incl. Battery), toggle/block helpers           | more sections from remaining inline template | `js/settings/`                      | `SettingsPage*.test.js`, `settingsSections.test.js`, `behaviorContracts.test.js` |
| `features/messages/components/ConversationViewer.svelte` | `composer/`, `modals/`, `outbound/`, `lib/lxmf/`, telemetry, helpers | further script slices                        | `lib/conversationMessageHelpers.ts` | ConversationViewer tests                                                         |
| `call/CallPage.vue`                                      | `call/tabs/`, `call/audio/`, `CallOverlay.vue`                       | more tabs and audio panels                   | call helpers                        | `CallPage*.test.js`                                                              |
| `map/MapPage.vue`                                        | `map/internal/` (panels + helpers, incl. MapSaveDrawingModal)        | more overlays and modals into `internal/`    | `js/map*`                           | map component tests                                                              |
| `relay/RelayChatPage.vue`                                | relay view components                                                | further relay panels as needed               | `js/relay*`                         | relay tests                                                                      |
| `App.vue`                                                | `layout/AppShellBanners.vue`, `layout/AppIdentitySwitchOverlay.vue`  | more shell chrome under `layout/`            | registries, WS shell                | `AppIdentitySwitch.test.js`                                                      |
| `network-visualiser/NetworkVisualiser.vue`               | `network-visualiser/internal/`                                       | more chrome into `internal/`                 | `js/networkVisualiser*`             | network visualiser tests                                                         |
| `interfaces/AddInterfacePage.vue`                        | `interfaces/internal/AddInterfaceDiscoveryPanel.vue`                 | further interface form panels                | `js/interfaceDiscoveryUtils.js`     | AddInterface tests                                                               |

Frontend ownership contracts:

- `tests/frontend/fixtures/frontend_mega_page_ownership.json`
- `tests/frontend/fixtures/frontend_symbol_continuity/`
- `tests/frontend/frontendOwnershipContract.test.js`

## Contract ownership

| Contract                  | Owner files                                                                                                                                                      |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| HTTP route inventory      | `tests/backend/fixtures/http_api_routes.json`, scanners in `http_api_contract_helpers.py` (reads `meshchat.py` and `backend/http/**/*.py`)                       |
| HTTP JSON GET schemas     | `http_api_response_schemas.py`, `http_api_response_registry.py`                                                                                                  |
| Core status/auth/app_info | `api_json_contract_schemas.py`                                                                                                                                   |
| WS message manifest       | `tests/backend/fixtures/ws_message_manifest.json`, `ws_contract_helpers.py` (reads `meshchat.py`, `backend/http/**/*.py`, `lifecycle/**`, `rns_link_manager.py`) |
| Schema version manifest   | `tests/backend/fixtures/schema_versions/manifest.json`, `schema_versions_contract_helpers.py` (reads `DatabaseSchema.LATEST_VERSION`)                            |
| Backend table itself      | `tests/backend/fixtures/backend_module_ownership.json`, `test_module_ownership_contract.py` (parses this doc's Backend table and checks paths exist)             |

Schema contracts stay in `tests/backend/`. Route and WS owners are production modules under `backend/http/`.

All four fixtures above are generator-checked, not hand-edited: each owning test derives the
expected structure from source and fails on drift, with an `UPDATE_HTTP_API_ROUTES=1` /
`UPDATE_WS_MESSAGE_MANIFEST=1` / `UPDATE_SCHEMA_VERSIONS_MANIFEST=1` / `UPDATE_BACKEND_MODULE_OWNERSHIP=1`
escape hatch to rewrite the fixture, matching the `UPDATE_FRONTEND_OWNERSHIP=1` pattern used by
`tests/frontend/frontendOwnershipContract.test.js`.
