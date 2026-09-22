---
name: reticulum-stack
description: Reticulum identities, destination hashes, aspects, announces, path requests, and links as used in MeshChatX. Use when addressing peers, adding a mesh app aspect, storing announces, or requesting a path.
---

# Skill: reticulum-stack

Reticulum is a cryptography-based networking stack for local and wide-area networks, including high-latency and low-bandwidth links. MeshChatX is a client on that stack. It is not a REST mesh and not an IP overlay with extra steps.

Site: [reticulum.network](https://reticulum.network/).
Philosophy: [Zen of Reticulum](https://reticulum.network/manual/zen.html).
Gates: reticulum-design-gates. Interfaces: reticulum-interfaces.

## When to use

- Addressing a peer, storing a favourite, or opening a path
- Adding or changing a destination aspect
- Announce ingest, display names, or path-table behaviour
- Anything that looks like "we need a server / DNS / hostname to find people"

## Facts that do not move

From the Reticulum manual and [reticulum.network](https://reticulum.network/):

- Packets do not carry a source address.
- There is no central address registry. Anyone can allocate destination hashes from an identity key.
- An address is a hash of an identity, not a location. Move the key, keep the hash.
- Newly generated destinations become reachable after announce and path discovery (seconds to a few minutes on a working mesh).
- Encryption is on by default. Keys are ephemeral. Forward secrecy is the default.
- Unencrypted links cannot be established. Unencrypted packets to a destination are dropped as invalid.

MeshChatX mapping:

- Cryptographic identity lives under storage/identities/<identity_hash>/identity.
- Display names are local labels on that hash. They are not network addresses.
- Shared Reticulum config is ~/.reticulum unless --reticulum-config-dir / MESHCHAT_RETICULUM_CONFIG_DIR / MESHCHAT_DATA_DIR overrides it.
- Identity switch does not reset ~/.reticulum.

## Destination plus aspect

Address peers as destination hash + aspect. Do not store host:port as the mesh address.

Aspects MeshChatX already uses:

| Aspect            | Meaning              |
| ----------------- | -------------------- |
| lxmf.delivery     | LXMF mail            |
| lxmf.propagation  | Propagation node     |
| lxst.telephony    | LXST calls           |
| nomadnetwork.node | NomadNet page server |
| rrc.hub           | Relay Chat hub       |
| map-data-v1       | Published map packs  |

Custom apps get their own aspect (example from design gates: mcx-bugs-v1). Do not overload lxmf.delivery for non-mail traffic. RNS Link API aspects are dot-separated app name plus sub-aspects (example microrn.mgmt).

Announce ingest caps and store toggles live in announce_manager.py (announce_max_stored__, announce_store__, announce_fetch_limit_*).

## Path and delay

Missing path: request a path, allow LXMF propagate where that is the protocol, show a recoverable outbound state. Do not spin the UI until an ACK arrives on a LoRa-class link.

Do not pin a 15 second (or any fixed) timer for cold path requests or first-hop link setup. Reticulum already knows the interface bitrate.

- Path wait: meshchatx/src/backend/path_utils.py path_response_window. Uses RNS.Reticulum.get_instance().get_first_hop_timeout() (not RNS.Transport.first_hop_timeout(), which is wrong on a shared rnsd client) plus an airtime floor from the slowest online interface bitrate, clamped to RNS.Reticulum.MINIMUM_BITRATE (5 bps).
- Link wait: link.establishment_timeout plus LINK_ESTABLISHMENT_MARGIN_S via link_establishment_window. Pass None so callers do not override RNS.

Links are live sessions on top of paths. LXST calls and RRC hubs use links. LXMF mail is store-and-forward and must survive a missing path.

## Key files

- meshchatx/src/backend/identity_context.py
- meshchatx/src/backend/identity_manager.py
- meshchatx/src/backend/announce_manager.py
- docs/en/identity-and-security.md
- docs/en/architecture.md

## Refuse

- Required fetch(https://...) to deliver LXMF or discover peers
- New global name registry or "default discovery server" for core reachability
- Treating the local HTTPS UI as the mesh
- Logging private keys or unredacted identity material by default
