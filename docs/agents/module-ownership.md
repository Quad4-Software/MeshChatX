# Module ownership map

Domain ownership for MeshChatX. Use this when deciding where code and tests live.
Orchestration entry remains `meshchatx.meshchat` (`ReticulumMeshChat`, `main`).

Schema contracts live under `tests/backend/` (not production route modules).

## Backend

| Domain            | Manager modules                                               | HTTP route module                           | WS module                    | Primary tests                                                    | Frontend page                                         |
| ----------------- | ------------------------------------------------------------- | ------------------------------------------- | ---------------------------- | ---------------------------------------------------------------- | ----------------------------------------------------- |
| Identity          | `identity_context.py`, `identity_manager.py`                  | `http/routes/identities.py`                 | `http/ws/dispatch.py`        | `test_identity_*`, identity-switch skills                        | Identities / tutorial                                 |
| Status / startup  | `lifecycle/deferred_network.py`, `rns_startup_recovery.py`    | `http/routes/status.py`                     | (status via REST)            | `test_deferred_network_startup.py`, `test_api_json_contracts.py` | App shell banners                                     |
| Auth / CSRF       | `csrf.py`, `app_security_settings.py`, `ip_allowlist.py`      | `http/routes/auth.py`                       | `http/ws/dispatch.py`        | `test_csrf*`, `test_access_attempts_*`                           | Auth gate in `App.vue`                                |
| Messages / LXMF   | `message_handler.py`, `lxmf_utils.py`, `database/messages.py` | `http/routes/messages.py`, `lxmf.py`        | `http/ws/dispatch.py`        | LXMF messaging skill tests                                       | `messages/MessagesPage.vue`, `ConversationViewer.vue` |
| Telephone / LXST  | `telephone_manager.py`, `database/telephone.py`               | `http/routes/telephone.py`, `contacts.py`   | `http/ws/dispatch.py`        | telephone contract tests                                         | `call/CallPage.vue`                                   |
| RRC               | `rrc/manager.py`, `rrc/server.py`                             | `http/routes/rrc.py`                        | `http/ws/dispatch.py`        | RRC skill tests                                                  | `relay/RelayChatPage.vue`                             |
| Map               | `map_manager.py`, `map_overlay_manager.py`                    | `http/routes/map.py`                        | marker updates via broadcast | map manager tests                                                | `map/MapPage.vue`                                     |
| Plugins           | `plugin_manager.py`, `plugin_permissions.py`                  | `http/routes/plugins.py`, `sideband.py`     | `http/ws/dispatch.py`        | plugin install security tests                                    | `settings/PluginsSettingsSection.vue`                 |
| FileSync          | `rns_filesync_handler.py`                                     | `http/routes/filesync.py`                   | (REST-heavy)                 | filesync security tests                                          | `filesync/` pages                                     |
| Interfaces        | `interface_editor.py`, `interface_config_parser.py`           | `http/routes/interfaces.py`                 | (announce loops on app)      | interface stats tests                                            | `interfaces/InterfacesPage.vue`                       |
| Database / backup | `database/*`, `recovery/*`                                    | `http/routes/database.py`, `maintenance.py` | (broadcasts on restore)      | backup/restore skill tests                                       | About / maintenance settings                          |
| Docs              | `docs_manager.py`                                             | `http/routes/docs.py`                       | (none)                       | docs manager tests                                               | `docs/DocsPage.vue`                                   |
| Sandbox           | `landlock_sandbox.py`, `seccomp_sandbox.py`                   | `http/routes/status.py`                     | (none)                       | landlock/seccomp tests                                           | Web exposure settings                                 |
| RNS Link API      | `rns_link_manager.py`                                         | (WS only)                                   | `http/ws/dispatch.py`        | `test_rns_link_*`                                                | plugins / external tools                              |
| Config            | `config_manager.py`                                           | `http/routes/config.py`                     | `http/ws/dispatch.py`        | settings config services tests                                   | `settings/SettingsPage.vue`                           |

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

| Page shell                        | Child dirs                                                               | Shared JS                       | Primary tests                                                                    |
| --------------------------------- | ------------------------------------------------------------------------ | ------------------------------- | -------------------------------------------------------------------------------- |
| `settings/SettingsPage.vue`       | `settings/sections/`, `SettingToggleRow.vue`, `SettingsSectionBlock.vue` | `js/settings/`                  | `SettingsPage*.test.js`, `settingsSections.test.js`, `behaviorContracts.test.js` |
| `messages/ConversationViewer.vue` | `messages/composer/`, `modals/`, `outbound/`, `lxmf/`                    | `conversationMessageHelpers.js` | ConversationViewer tests                                                         |
| `call/CallPage.vue`               | `call/tabs/`, `call/audio/`                                              | call helpers                    | `CallPage*.test.js`                                                              |
| `map/MapPage.vue`                 | `map/internal/`                                                          | `js/map*`                       | map component tests                                                              |
| `relay/RelayChatPage.vue`         | relay view components                                                    | `js/relay*`                     | relay tests                                                                      |
| `App.vue`                         | `layout/`                                                                | registries, WS shell            | `AppIdentitySwitch.test.js`                                                      |

## Contract ownership

| Contract                  | Owner files                                                                                                                                                      |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| HTTP route inventory      | `tests/backend/fixtures/http_api_routes.json`, scanners in `http_api_contract_helpers.py` (reads `meshchat.py` and `backend/http/**/*.py`)                       |
| HTTP JSON GET schemas     | `http_api_response_schemas.py`, `http_api_response_registry.py`                                                                                                  |
| Core status/auth/app_info | `api_json_contract_schemas.py`                                                                                                                                   |
| WS message manifest       | `tests/backend/fixtures/ws_message_manifest.json`, `ws_contract_helpers.py` (reads `meshchat.py`, `backend/http/**/*.py`, `lifecycle/**`, `rns_link_manager.py`) |

Schema contracts stay in `tests/backend/`. Route and WS owners are production modules under `backend/http/`.
