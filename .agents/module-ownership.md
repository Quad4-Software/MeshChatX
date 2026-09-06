# Module ownership map

Domain ownership for MeshChatX. Use this when deciding where code and tests live.
Orchestration entry remains meshchatx.meshchat (ReticulumMeshChat, main).

Schema contracts live under tests/backend/ (not production route modules).

## Backend

| Domain            | Manager modules                                                      | HTTP route module           | WS module                    | Primary tests                                                                              | Frontend page                                                                                     |
| ----------------- | -------------------------------------------------------------------- | --------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| Identity          | identity_context/, identity_manager.py                           | identities/               | http/ws/dispatch.py        | test_identity_*, identity-switch skills                                                  | features/settings/components/IdentitiesPage.svelte, tutorial                                    |
| Status / startup  | lifecycle/deferred_network.py, rns_startup_recovery.py           | status/                   | (status via REST)            | test_deferred_network_startup.py, test_api_json_contracts.py                           | App shell banners                                                                                 |
| Auth / CSRF       | csrf.py, app_security_settings.py, ip_allowlist.py             | auth/                     | http/ws/dispatch.py        | test_csrf*, test_access_attempts_*                                                     | Auth gate in features/app-shell/                                                                |
| Messages / LXMF   | message_handler.py, lxmf_utils/, database/messages/            | messages/, lxmf/        | http/ws/dispatch.py        | LXMF messaging skill tests                                                                 | features/messages/MessagesPage.svelte, features/messages/components/ConversationViewer.svelte |
| Telephone / LXST  | telephone_manager/, database/telephone.py                        | telephone/, contacts/   | http/ws/dispatch.py        | telephone contract tests                                                                   | features/call/CallPage.svelte                                                                   |
| RRC               | rrc/manager/, rrc/server/                                        | rrc/                      | http/ws/dispatch.py        | RRC skill tests                                                                            | features/relay-chat/components/RelayChatPage.svelte                                             |
| Map               | map_manager.py, map_overlay_manager/, map_data_manager/        | map/                      | marker updates via broadcast | map manager tests                                                                          | features/map/MapPage.svelte                                                                     |
| Plugins           | plugin_manager/, plugin_permissions.py                           | plugins/, sideband/     | http/ws/dispatch.py        | plugin install security tests                                                              | features/settings/components/sections/PluginsSettingsSection.svelte                             |
| FileSync          | rns_filesync_handler/                                              | filesync/                 | (REST-heavy)                 | filesync security tests                                                                    | features/filesync/ pages                                                                        |
| Interfaces        | interface_editor.py, interface_config_parser.py                  | interfaces/               | (announce loops on app)      | interface stats tests                                                                      | features/interfaces/InterfacesPage.svelte                                                       |
| Database / backup | database/*, recovery/*                                           | database/, maintenance/ | (broadcasts on restore)      | backup/restore skill tests                                                                 | About / maintenance settings                                                                      |
| Docs              | docs_manager/                                                      | docs/                     | (none)                       | docs manager tests                                                                         | features/docs/DocsPage.svelte                                                                   |
| Sandbox           | landlock_sandbox.py, seccomp_sandbox.py, appcontainer_sandbox/ | status/                   | (none)                       | test_landlock_sandbox.py, test_landlock_integration_surfaces.py, sqlite landlock tests | Web exposure settings                                                                             |
| RNS Link API      | rns_link_manager.py                                                | (WS only)                   | http/ws/dispatch.py        | test_rns_link_*                                                                          | plugins / external tools                                                                          |
| Config            | config_manager/                                                    | config/                   | http/ws/dispatch.py        | settings config services tests                                                             | features/settings/components/SettingsPage.svelte                                                |

## HTTP package layout

```
meshchatx/src/backend/http/
  context.py
  errors.py
  live_names.py
  middleware.py
  register.py
  routes/<domain>/              # domain packages export register_<domain>_routes
    __init__.py                 # must export register_<domain>_routes
    _names.py                   # optional shared meshchat_names imports
    <slice>.py
  routes/__init__.py
  ws/dispatch.py
```

register_all_routes(routes, app) is the sole composition entry. Call it only from
ReticulumMeshChat._define_routes. Domain register functions are listed in fixed order
in routes/__init__.py. Free names resolve through live_names.inject_meshchat_names.

Fat route modules may become packages under the same domain name. The import path
meshchatx.src.backend.http.routes.<domain> must still provide register_<domain>_routes.

WS inbound handlers live in ws/handlers_*.py and are composed by ws/dispatch.py.

Manager modules may become packages that re-export the previous public class from the
old import path. Follow .agents/skills/meshchat-orchestration-split/SKILL.md.

## Frontend mega-pages

Placement for extracts and feature modules. Follow .agents/skills/svelte-feature-modules/SKILL.md.
Do not invent folders outside this table.

| Kind                            | Put it here                                               | Example                                |
| ------------------------------- | --------------------------------------------------------- | -------------------------------------- |
| Page-private panel or UI        | features/<id>/components/                               | MapSearchBar                           |
| Settings chunk                  | features/settings/components/sections/*.svelte          | TelephonySettingsSection               |
| Pure logic                      | colocated *.ts or js/<feature>/                       | clusterUtils, settingsConfigService    |
| Cross-feature primitive         | ui/svelte/                                              | ConfirmDialog, Toggle                  |
| Feature module (new / migrated) | features/<id>/ (page + index.ts register)             | features/blocked/                    |
| Nav, tools, commands, routes    | js/registries/ only                                     | never grow App.svelte / main.ts tables |
| Shell chrome / page host        | features/app-shell/, shell/                           | App.svelte, hashRouter, PageOutlet     |

| Page shell                                                        | On-disk child dirs                                                   | Planned child dirs                           | Shared JS                           | Primary tests                                                                    |
| ----------------------------------------------------------------- | -------------------------------------------------------------------- | -------------------------------------------- | ----------------------------------- | -------------------------------------------------------------------------------- |
| features/settings/components/SettingsPage.svelte                | features/settings/components/sections/, cards and toggle helpers   | more sections from remaining inline template | js/settings/                      | SettingsPage*.test.js, settingsSections.test.js, behaviorContracts.test.js |
| features/messages/components/ConversationViewer.svelte          | composer/, modals/, outbound/, lib/lxmf/, telemetry, helpers | further script slices                        | lib/conversationMessageHelpers.ts | ConversationViewer tests                                                         |
| features/call/CallPage.svelte                                   | features/call/components/, features/call/lib/                    | overlay mounted from app-shell               | call libs                           | CallPage*.test.js, CallOverlay.test.js                                       |
| features/map/MapPage.svelte                                     | features/map/components/, features/map/lib/                      | panels, modals, toolbars                     | features/map/lib/                 | map component tests                                                              |
| features/relay-chat/components/RelayChatPage.svelte             | features/relay-chat/components/                                    | further relay panels as needed               | features/relay-chat/lib/          | relay tests                                                                      |
| features/app-shell/App.svelte                                   | features/app-shell/components/, features/app-shell/lib/          | banners, sidebar, overlays                   | registries, WS shell                | hostFlipReadiness.test.js, shell regression tests                              |
| features/network-visualiser/components/NetworkVisualiser.svelte | features/network-visualiser/components/                            | toolbar, legend, overlays                    | features/network-visualiser/lib/  | network visualiser tests                                                         |
| features/interfaces/AddInterfacePage.svelte                     | features/interfaces/components/                                    | further interface form panels                | features/interfaces/lib/          | AddInterface tests                                                               |

Frontend ownership contracts:

- tests/frontend/fixtures/frontend_mega_page_ownership.json
- tests/frontend/fixtures/frontend_symbol_continuity/
- tests/frontend/frontendOwnershipContract.test.js

## Contract ownership

| Contract                  | Owner files                                                                                                                                                      |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| HTTP route inventory      | tests/backend/fixtures/http_api_routes.json, scanners in http_api_contract_helpers.py (reads meshchat.py and backend/http/**/*.py)                       |
| HTTP JSON GET schemas     | http_api_response_schemas.py, http_api_response_registry.py                                                                                                  |
| Core status/auth/app_info | api_json_contract_schemas.py                                                                                                                                   |
| WS message manifest       | tests/backend/fixtures/ws_message_manifest.json, ws_contract_helpers.py (reads meshchat.py, backend/http/**/*.py, lifecycle/**, rns_link_manager.py) |
| Schema version manifest   | tests/backend/fixtures/schema_versions/manifest.json, schema_versions_contract_helpers.py (reads DatabaseSchema.LATEST_VERSION)                            |
| Backend table itself      | tests/backend/fixtures/backend_module_ownership.json, test_module_ownership_contract.py (parses this doc's Backend table and checks paths exist)             |

Schema contracts stay in tests/backend/. Route and WS owners are production modules under backend/http/.

All four fixtures above are generator-checked, not hand-edited: each owning test derives the
expected structure from source and fails on drift, with an UPDATE_HTTP_API_ROUTES=1 /
UPDATE_WS_MESSAGE_MANIFEST=1 / UPDATE_SCHEMA_VERSIONS_MANIFEST=1 / UPDATE_BACKEND_MODULE_OWNERSHIP=1
escape hatch to rewrite the fixture, matching the UPDATE_FRONTEND_OWNERSHIP=1 pattern used by
tests/frontend/frontendOwnershipContract.test.js.
