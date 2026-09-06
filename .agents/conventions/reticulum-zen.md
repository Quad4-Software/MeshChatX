# Reticulum Zen conventions

Philosophy: https://reticulum.network/manual/zen.html
Checklist: `.agents/skills/reticulum-design-gates/SKILL.md`.

## Mental model

- No cloud center. Peers inhabit a fabric. No privileged server, registry, or landlord API for mesh features.
- Destination hashes are identity, not location. Do not bind reachability to IP, hostname, DNS, or one interface.
- Every link and peer is hostile. Encryption and proof are required.
- Bandwidth and airtime are scarce. Small payloads, async delivery, store-and-forward.
- Interfaces are clothing. App code talks destinations and aspects, not WiFi vs LoRa vs TCP.
- Announces are presence. Do not invent a central directory when announce + path discovery exist.
- Tools have ethics. No surveillance, extraction, kill-chain, or identity-tracking that fights local-first sovereignty.

## Hard no

1. No required clearnet HTTP/SaaS for core mesh messaging, identity, or pathfinding.
2. Do not treat LXMF / RNS as a synchronous WebSocket that must stay online.
3. Do not log or ship full identity private keys without explicit user action and redaction defaults.
4. No new global registries that map people to locations or force one naming authority.
5. No plaintext mesh protocols "for convenience".
6. Do not block the UI forever waiting for a path. Queue, retry, propagate, or fail recoverably.
7. Do not couple feature logic to one physical medium or interface type.
8. Do not weaken plugin permission, RSG, CSRF, or auth to ship a demo.

## Hard yes

1. Address peers by destination / identity hash. Names are local labels on a keyring.
2. Use aspects correctly (`lxmf.delivery`, `lxst.telephony`, `rrc.hub`, custom app aspects). Do not overload `lxmf.delivery` for non-LXMF apps.
3. Design for intermittent links: send, continue, handle delivery later.
4. Keep mesh payloads minimal. Truncate previews. Chunk large transfers with existing tools.
5. Prefer existing RNS / LXMF / LXST primitives over bespoke transports.
6. Keep identity-scoped state inside `IdentityContext`. No cross-identity leakage.
7. Privacy mode and Landlock stay intact. Clearnet fetches stay opt-in and gated.

## MeshChatX mapping

| Zen idea            | MeshChatX reality                                             |
| ------------------- | ------------------------------------------------------------- |
| Portable identity   | `storage/identities/<hash>/`, identity switch teardown        |
| Announce presence   | announce handlers, favourites, path table                     |
| Store and forward   | LXMF propagation, outbound delivery states                    |
| Transport agnostic  | Reticulum interfaces config, not app-level sockets            |
| Scarcity            | slim conversation queries, stamps, attachment discipline      |
| Cryptographic trust | destination recall, proofs. Local HTTPS UI is not mesh crypto |

## Before shipping mesh-facing code

Run `.agents/skills/reticulum-design-gates/SKILL.md`. Fail any gate means redesign: clearnet-disabled mesh paths, destination hash + aspect, delay/missing-path tolerance, payload size, hostile-transport secrecy, identity redaction, no cross-identity leakage.
