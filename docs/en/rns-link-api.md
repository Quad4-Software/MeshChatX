# Generic RNS Link API

MeshChatX exposes a generic Reticulum Link transport over the main WebSocket (`/ws`) so external apps and plugins can open links, run request/response exchanges, send packets, and tear links down without going through NomadNet-specific helpers.

This is the surface used by microReticulum management consoles that treat MeshChatX as an RNS transport.

## Auth

When password auth is enabled, all `rns.link.*` client messages require an authenticated session (same rule as other WebSocket mutators).

## Client → server

| `type`              | Fields                                                                             | Behavior                                                                                                                        |
| ------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `rns.link.open`     | `destination_hash` (hex), `aspect` (dot-separated), `request_id`, `auto_identify?` | Open or reuse a cached link to `(aspect, destination_hash)`. Streams `phase` then `success` / `failure`.                        |
| `rns.link.identify` | `destination_hash`, `aspect`, `request_id`                                         | Call `link.identify(local_identity)` on the cached link.                                                                        |
| `rns.link.request`  | `destination_hash`, `aspect`, `path`, `request_id`, `data_b64?`, `timeout?`        | Ensure the link is open, then `link.request(path, data=…)`. `data_b64` / reply `body_b64` are msgpack payloads, base64-encoded. |
| `rns.link.send`     | `destination_hash`, `aspect`, `payload_b64`, `request_id`                          | Send a raw packet on the cached link.                                                                                           |
| `rns.link.close`    | `destination_hash`, `aspect`, `request_id`                                         | Teardown and uncache the link.                                                                                                  |

`aspect` is split on `.` into RNS app name + sub-aspects (for example `microrn.mgmt`).

Long-running `open` / `request` work is tracked per WebSocket client and cancelled when that client disconnects.

## Server → client

Per-`request_id` replies reuse the same `type` with `status` of `phase`, `progress`, `success`, or `failure`.

Broadcast events:

| `type`           | `event`           | Notes                  |
| ---------------- | ----------------- | ---------------------- |
| `rns.link.event` | `packet_received` | Includes `payload_b64` |
| `rns.link.event` | `link_closed`     | Cached link removed    |

## Plugin capabilities

Plugins that declare the matching `permissions.managers` entries can call the same transport through `POST /api/v1/plugins/{id}/invoke` with `method: "callManager"`:

- `rnsLink.open`
- `rnsLink.identify`
- `rnsLink.request`
- `rnsLink.send`
- `rnsLink.close`

Subscribe to async link traffic with `permissions.hooks: ["rns.link.event"]`. Events arrive as `plugin.event` WebSocket frames with `event: "rns.link.event"`.

Example manifest fragment:

```json
{
    "permissions": {
        "hooks": ["rns.link.event"],
        "managers": ["rnsLink.open", "rnsLink.identify", "rnsLink.request", "rnsLink.send", "rnsLink.close"],
        "storage": "isolated",
        "network": "none"
    }
}
```

## Implementation

- `meshchatx/src/backend/rns_link_manager.py` — link cache, open/identify/request/send/close
- `meshchatx/meshchat.py` — WebSocket dispatch and per-client task tracking
- `meshchatx/src/backend/plugin_manager.py` — capability wrappers and hook fan-out

## Related

- **Plugins** in Tools docs for install/enable flow
- **Architecture** for the plugin runtime overview
