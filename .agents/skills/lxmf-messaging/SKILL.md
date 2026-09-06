---
name: lxmf-messaging
description: LXMF send/receive, stamps, propagation nodes, attachments, inbound cancel. Use when changing messaging, LXMRouter wiring, or conversation UI.
---

# Skill: lxmf-messaging

Change LXMF messaging, stamps, propagation, or attachments without breaking local-first mesh delivery or identity scoping.

## When to use

- Outbound/inbound LXMF, conversations, receipts, stamps
- Propagation nodes, sync, inbound cancel, transfer limits
- Attachments, images, RNCP handoff from chat
- Config knobs that map to LXMRouter behaviour

## Intent

LXMF is store-and-forward mail on Reticulum. Do not require clearnet, DNS, or a central API to deliver messages. Address peers by destination hash and aspect lxmf.delivery.

## Key paths

| Area                     | Path                                                                                               |
| ------------------------ | -------------------------------------------------------------------------------------------------- |
| Identity / router wiring | meshchatx/src/backend/identity_context.py                                                        |
| Message handler          | meshchatx/src/backend/message_handler.py (and related)                                           |
| HTTP/WS surface          | meshchatx/meshchat.py                                                                            |
| Inbound cancel helpers   | meshchatx/src/backend/meshchat_utils.py (list_inbound_deliveries, cancel_inbound_deliveries) |
| Frontend conversations   | meshchatx/src/frontend/features/messages/                                      |
| Config                   | config managers / settings UI for LXMF options                                                     |

## LXMF 1.1 / RNS 1.4 inbound cancel

Large inbound LXMF deliveries use RNS Resources. LXMF exposes:

- LXMRouter.inbound_resources() / inbound_count()
- cancel_inbound(resource_hash) and cancel_all_inbound()

MeshChatX surfaces them as:

- Status: inbound_delivery_count and inbound_deliveries on /api/v1/lxmf/propagation-node/status
- Cancel: POST /api/v1/lxmf/propagation-node/cancel-inbound with optional { "resource_hash": "..." }
- Banner UI in AppShellBanners when active inbound transfers exist

Outbound cancel remains POST /api/v1/lxmf-messages/{hash}/cancel via cancel_outbound.

Keep minimum versions: rns>=1.5.2, lxmf>=1.1.1.

## Gates

1. Missing path: request path, allow propagate, surface recoverable state. No infinite spinner for LoRa-class delay.
2. Payload size justified. Large files use RNCP or explicit transfer tools, not giant chat blobs.
3. No cross-identity inbox or cache sharing.
4. Do not log private keys or unredacted message bodies by default.
5. Stamp and validation settings must match installed lxmf/rns versions.

## Verification

Prefer focused backend tests around the changed manager, plus frontend tests when UI sends or displays messages.

```bash
uv run pytest tests/backend/test_phased_startup_guards.py -q --tb=short
```

Also: reticulum-design-gates, deferred-network-startup, identity-switch-teardown.
