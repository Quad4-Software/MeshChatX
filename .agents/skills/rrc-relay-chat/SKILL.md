---
name: rrc-relay-chat
description: Reticulum Relay Chat hubs, rooms, +k keys, moderation, client state. Use when changing RRC protocol, hub hosting, or Relay Chat UI.
---

# Skill: rrc-relay-chat

Implement or harden Reticulum Relay Chat (RRC) hubs and clients without breaking membership, +k keys, or identity scoping.

## When to use

- Relay Chat UI, HTTP/WS APIs, hub hosting, moderation commands
- Room keys (+k), invite-only (+i), kick/ban/part behaviour
- Client history, auto-rejoin, stored room keys
- Spec alignment with https://rrc.kc1awv.net/ (hub conventions such as +k are rrcd-compatible extensions)

## Core model

- Aspect: `rrc.hub`. Address hubs by destination hash, not IP.
- Hub-and-spoke over RNS Links. Rooms are hub-local labels.
- JOIN body is empty in core wire docs. MeshChatX hubs may put a room key string in the JOIN body for +k.
- Local HTTPS UI is not the mesh. Peers are not REST clients of MeshChatX.

## Key paths

| Area              | Path                                              |
| ----------------- | ------------------------------------------------- |
| Protocol          | `meshchatx/src/backend/rrc/protocol.py`           |
| Client hubs       | `meshchatx/src/backend/rrc/manager.py`            |
| Hosted hub        | `meshchatx/src/backend/rrc/server.py`             |
| Commands          | `meshchatx/src/backend/rrc/hub_commands.py`       |
| Room ACL          | `meshchatx/src/backend/rrc/room_registry.py`      |
| rooms.toml        | `meshchatx/src/backend/rrc/rooms_toml.py`         |
| Client key crypto | `meshchatx/src/backend/rrc/room_key_crypto.py`    |
| Key DAO           | `meshchatx/src/backend/database/rrc_room_keys.py` |
| UI                | `meshchatx/src/frontend/components/relay/`        |

## Non-negotiables

1. Do not promote founder/ops before +k / +i checks pass.
2. Non-member PART must not fan out PARTED.
3. Kick/ban must fan PARTED to remaining members and force client leave on ERROR.
4. Client room keys: AES-GCM wrapped with HKDF from identity private key. Never return plaintext keys from list APIs.
5. Hub room keys may live in rooms.toml (hub-local). Public API exposes `has_key` only.
6. Quote rooms.toml table names so dotted room names roundtrip.
7. Identity-scoped state only. Removing a hub clears stored keys for that hub.

## Modes (hub conventions)

| Flag | Meaning                                      |
| ---- | -------------------------------------------- |
| +k   | Key required to JOIN (unless op or invited)  |
| +i   | Invite-only                                  |
| +n   | No outside messages (non-members cannot MSG) |
| +m   | Moderated (need voice)                       |
| +p   | Private (hide from list / who restrictions)  |
| +t   | Topic ops-only                               |

Without +n, non-members can MSG an existing room (IRC-like). Kick removes membership. Enable +n if kicked users must stay silent.

## Tests

```bash
uv run pytest tests/backend/test_rrc_oracle_bugs.py tests/backend/test_rrc_room_keys.py tests/backend/test_rrc_server.py tests/backend/test_rrc_moderation.py -q --tb=short
pnpm exec vitest run tests/frontend/RelayChatPage.test.js
```

Use oracle and exploratory skills when hunting RRC bugs.
