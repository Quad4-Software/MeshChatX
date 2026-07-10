# Reticulum Zen conventions

Source philosophy: [Zen of Reticulum](https://reticulum.network/manual/zen.html).
This file turns that philosophy into hard gates for MeshChatX work.
Full checklist: `docs/agents/skills/reticulum-design-gates/SKILL.md`.

## Mental model (required)

- There is no cloud center. Peers inhabit a fabric. Do not design features that need a privileged server, registry, or landlord API to function on the mesh.
- Destination hashes are identity, not location. Do not bind mesh reachability to IP, hostname, DNS, or a fixed interface.
- Assume every link and peer is hostile. Encryption and cryptographic proof are not optional add-ons.
- Bandwidth and airtime are scarce. Prefer small payloads, async delivery, and store-and-forward over chatty request/response.
- Interfaces are clothing. Application code talks to destinations and aspects, not to WiFi vs LoRa vs TCP specifics.
- Announces are presence. Do not invent a central directory when announce + path discovery already solve discovery.
- Tools have ethics. Do not add surveillance, extraction, kill-chain, or identity-tracking features that fight local-first sovereignty.

## Hard no

1. Do not require clearnet HTTP/SaaS for core mesh messaging, identity, or pathfinding.
2. Do not treat LXMF / RNS as "just another WebSocket API" that must stay online synchronously.
3. Do not store or ship full identity private keys in logs, bug reports, UI dumps, or plugin storage without explicit user action and redaction defaults.
4. Do not invent new global registries that map people to locations or force a single naming authority.
5. Do not add plaintext mesh protocols "for convenience".
6. Do not block the UI forever waiting for a path. Queue, retry, propagate, or fail with a recoverable state.
7. Do not couple feature logic to one physical medium or one interface type.
8. Do not weaken plugin permission, RSG, CSRF, or auth gates to "make demos easier".

## Hard yes

1. Address peers by destination / identity hash. User-facing names are local labels on a keyring.
2. Use aspects correctly (`lxmf.delivery`, `lxst.telephony`, `rrc.hub`, custom app aspects). Do not overload `lxmf.delivery` for non-LXMF apps.
3. Design for intermittent links: send, continue, handle delivery later.
4. Keep mesh payloads minimal. Truncate previews. Compress or chunk large transfers with existing tools (RNCP, attachments) instead of stuffing megabytes into chat fields.
5. Prefer existing RNS / LXMF / LXST primitives over bespoke transports.
6. Keep identity-scoped state inside `IdentityContext`. No cross-identity leakage.
7. Privacy mode and Landlock constraints stay intact. Clearnet fetches remain opt-in and gated.

## MeshChatX mapping

| Zen idea            | MeshChatX reality                                                       |
| ------------------- | ----------------------------------------------------------------------- |
| Portable identity   | `storage/identities/<hash>/`, identity switch teardown                  |
| Announce presence   | announce handlers, favourites, path table                               |
| Store and forward   | LXMF propagation nodes, outbound delivery states                        |
| Transport agnostic  | Reticulum interfaces config, not app-level socket code                  |
| Scarcity            | slim conversation queries, stamp costs, attachment discipline           |
| Cryptographic trust | destination recall, proofs, HTTPS local UI is separate from mesh crypto |

## Before you ship mesh-facing code

Answer all of these. If any answer is wrong, redesign.

1. Does this still work with no clearnet and only Reticulum interfaces up?
2. Does it address a destination hash / aspect, not an IP or URL, for mesh peers?
3. Can it tolerate minutes of delay or a missing path without corrupting state?
4. Is the wire payload as small as the intent allows?
5. Would a hostile transport node learn nothing useful beyond ciphertext and routing proofs?
6. Is identity material and personal metadata default-redacted in any export or bug path?
