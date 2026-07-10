# Skill: rns-link-api

Implement or consume the generic RNS Link WebSocket transport and plugin manager capabilities without breaking auth, caching, or disconnect cleanup.

## When to use

- Changing `rns.link.*` WebSocket handlers or `RnsLinkManager`
- Exposing link open/request/send to plugins
- Building external tools that treat MeshChatX as an RNS transport
- Debugging stuck opens, leaked links, or auth failures on link mutators

## Protocol (summary)

Client → server types: `rns.link.open|identify|request|send|close` with `request_id`.

- `aspect` is dot-separated RNS app name + sub-aspects (example `microrn.mgmt`).
- Payloads are msgpack, base64-encoded (`data_b64`, `payload_b64`, `body_b64`).
- Links are cached per `(aspect, destination_hash)`. `close` tears down and uncaches.
- In-flight `open` / `request` tasks cancel when that WebSocket client disconnects.
- Server replies reuse the same `type` with `status` of `phase` / `progress` / `success` / `failure`.
- Broadcasts: `rns.link.event` (`packet_received`, `link_closed`).

Full table: `docs/en/rns-link-api.md`.

## Auth and plugins

- When password auth is enabled, all `rns.link.*` client messages require an authenticated session (same as other WS mutators). See `auth-csrf-ws-security`.
- Plugins need `permissions.managers` entries such as `rnsLink.open` and optional `hooks: ["rns.link.event"]`.
- Invoke via `POST /api/v1/plugins/{id}/invoke` with `method: "callManager"`.
- New manager names must be added to `KNOWN_MANAGERS` (see `plugin-install-security`).

## Key files

- `docs/en/rns-link-api.md`
- `meshchatx/src/backend/rns_link_manager.py`
- `meshchatx/meshchat.py` (WS dispatch, per-client task tracking)
- `meshchatx/src/backend/plugin_manager.py`
- `meshchatx/src/backend/websocket_config_guard.py`

## Verification

```bash
uv run pytest tests/backend/test_rns_link_manager.py tests/backend/test_rns_link_plugin.py -q --tb=short
```
