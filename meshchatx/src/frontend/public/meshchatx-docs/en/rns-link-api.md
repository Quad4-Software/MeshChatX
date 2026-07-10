# RNS Link API

MeshChatX exposes a generic Reticulum Link transport on the main WebSocket (`/ws`). External apps and plugins can open links, run request/response exchanges, send packets, and tear links down without going through NomadNet helpers.

## When to use it

```
Your app or plugin needs a live RNS Link
    |
    --> Not NomadNet page browsing
    --> Not LXMF messaging
    |
    --> Use rns.link.* over /ws
        or plugin managers rnsLink.*
```

Address peers by destination hash and aspect. Do not invent IP or hostname shortcuts.

## Auth

When password auth is enabled, every `rns.link.*` client message needs an authenticated session. Same rule as other WebSocket mutators.

## Link lifecycle

```
Client sends rns.link.open
    |
    --> MeshChatX finds or opens path to destination
    |
    --> Link cached under (aspect, destination_hash)
    |
    --> Optional auto_identify
    |
    --> success / failure reply on same type + request_id
    |
    +--> rns.link.request / rns.link.send on the cached link
    |
    +--> rns.link.close tears down and uncaches
    |
    +--> disconnect cancels in-flight open / request for that client
```

Cache notes:

- Key is `(aspect, destination_hash)`
- Cap is 64 active links
- Idle links expire after about 30 minutes
- Repeated request failures recycle the cached link so the next call re-opens

## Client to server

All messages need a unique `request_id` so replies can be matched.

| `type`              | Required fields                                           | Optional              | Behaviour                                                                |
| ------------------- | --------------------------------------------------------- | --------------------- | ------------------------------------------------------------------------ |
| `rns.link.open`     | `destination_hash`, `aspect`, `request_id`                | `auto_identify`       | Open or reuse a cached link. Streams `phase` then `success` / `failure`. |
| `rns.link.identify` | `destination_hash`, `aspect`, `request_id`                |                       | Call `link.identify(local_identity)` on the cached link.                 |
| `rns.link.request`  | `destination_hash`, `aspect`, `path`, `request_id`        | `data_b64`, `timeout` | Ensure the link is open, then `link.request(path, data=…)`.              |
| `rns.link.send`     | `destination_hash`, `aspect`, `payload_b64`, `request_id` |                       | Send a raw packet on the cached link.                                    |
| `rns.link.close`    | `destination_hash`, `aspect`, `request_id`                |                       | Teardown and uncache the link.                                           |

Field details:

- `destination_hash`: hex string of the peer destination
- `aspect`: dot-separated RNS app name + sub-aspects, for example `microrn.mgmt`
- `data_b64` / `payload_b64` / reply `body_b64`: msgpack payloads, base64-encoded
- `path`: request path string on the remote link endpoint
- `timeout`: seconds for the request wait

Example open:

```json
{
    "type": "rns.link.open",
    "destination_hash": "aabbccddeeff00112233445566778899aabbccdd",
    "aspect": "microrn.mgmt",
    "request_id": "req-1",
    "auto_identify": true
}
```

Example request:

```json
{
    "type": "rns.link.request",
    "destination_hash": "aabbccddeeff00112233445566778899aabbccdd",
    "aspect": "microrn.mgmt",
    "path": "/status",
    "request_id": "req-2",
    "data_b64": null,
    "timeout": 15
}
```

## Server to client

Per-`request_id` replies reuse the same `type` with a `status`:

| `status`   | Meaning                                      |
| ---------- | -------------------------------------------- |
| `phase`    | Progress step while opening or requesting    |
| `progress` | Additional progress detail when available    |
| `success`  | Operation finished                           |
| `failure`  | Operation failed (includes an error message) |

Broadcast events (not tied to one `request_id`):

| `type`           | `event`           | Notes                  |
| ---------------- | ----------------- | ---------------------- |
| `rns.link.event` | `packet_received` | Includes `payload_b64` |
| `rns.link.event` | `link_closed`     | Cached link removed    |

```
Inbound packet on a cached link
    |
    --> Broadcast rns.link.event / packet_received
    |
Link torn down or evicted
    |
    --> Broadcast rns.link.event / link_closed
```

## Plugins

Plugins call the same transport through HTTP invoke instead of speaking WebSocket types directly.

```
Plugin Worker
    |
    --> POST /api/v1/plugins/{id}/invoke
        method: "callManager"
    |
    --> PluginManager checks granted managers
    |
    --> RnsLinkManager open / identify / request / send / close
```

Declare managers in `plugin.json`:

| Manager            | Maps to                 |
| ------------------ | ----------------------- |
| `rnsLink.open`     | Open or reuse link      |
| `rnsLink.identify` | Identify on cached link |
| `rnsLink.request`  | Request/response        |
| `rnsLink.send`     | Raw packet send         |
| `rnsLink.close`    | Teardown                |

Subscribe to async traffic with:

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

Hook delivery:

```
RnsLinkManager event
    |
    --> PluginManager.dispatch_hook("rns.link.event", …)
    |
    --> WebSocket plugin.event to the UI
    |
    --> Plugin Worker on_hook / event handler
```

## External app pattern

```
Connect to MeshChatX /ws (auth cookie / session as required)
    |
    --> Send rns.link.open with request_id
    |
    --> Wait for matching success
    |
    --> Send rns.link.request or rns.link.send
    |
    --> Listen for rns.link.event broadcasts
    |
    --> Send rns.link.close when finished
```

Keep one `request_id` per outstanding call. Cancel or ignore replies after you disconnect. MeshChatX cancels in-flight open/request work for that WebSocket client on disconnect.

## Limits and failure behaviour

- Missing path or unreachable peer returns `failure` on the open/request reply
- After repeated request failures on one cached link, MeshChatX recycles that link
- Idle unused links are swept after about 30 minutes
- Over-cap eviction drops the oldest unused links first

## Implementation map

```
/ws rns.link.*
    |
    --> meshchat.py WebSocket dispatch + per-client task tracking
    |
    --> rns_link_manager.py cache, open, identify, request, send, close
    |
    --> plugin_manager.py capability wrappers + hook fan-out
```

## See also

- [Plugins](plugins.md) for install, grants, and invoke flow
- [Architecture and design](architecture.md) for WebSocket and plugin runtime overview
- [Identities, privacy, and security](identity-and-security.md) for auth and session rules
