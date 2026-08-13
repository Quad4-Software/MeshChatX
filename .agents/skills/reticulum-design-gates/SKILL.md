---
name: reticulum-design-gates
description: Mesh design review against Zen of Reticulum and MeshChatX architecture. Use before any feature that sends, receives, discovers, or stores mesh data.
---

# Skill: reticulum-design-gates

Stop IP-era and cloud-era design mistakes before they land in MeshChatX.
Grounded in the [Zen of Reticulum](https://reticulum.network/manual/zen.html) and MeshChatX architecture.

## When to use

- Any feature that sends, receives, discovers, or stores mesh data
- New aspects, destinations, announces, links, or propagation behaviour
- Plugins that talk to the mesh
- Bug-report / telemetry / logging paths that might leak identity material
- "Quick" integrations that want HTTP, DNS, Firebase, or a central API "just for sync"

Also read: `.agents/conventions/reticulum-zen.md`, `.agents/skills/reticulum-stack/SKILL.md`, `.agents/overview.md`, `docs/en/architecture.md`.

## Gate 0: Intent

State in one sentence what the user can do offline on a LoRa-only mesh after this change.
If you cannot, you are probably designing a cloud client.

## Gate 1: No center

Reject designs that need any of:

- A mandatory cloud backend, CDN, or phone-home license server
- A global name registry or "default discovery server" for core reachability
- A privileged mesh node role that can read plaintext or revoke peers by policy

Allowed:

- Optional clearnet helpers behind privacy mode / explicit settings (docs fetch, community interface lists)
- Local HTTPS UI to the user's own MeshChatX process
- User-chosen propagation nodes and hubs

## Gate 2: Identity is a hash

- Peers are destination hashes (and related identity hashes), not IPs or hostnames.
- UI may show local display names. Those names are labels, not network addresses.
- Do not invent a new addressing scheme when RNS destinations + aspects already fit.
- Custom apps get their own aspect (example `mcx-bugs-v1`). Do not overload `lxmf.delivery` for non-LXMF traffic.

## Gate 3: Hostile medium

- Do not add plaintext mesh channels for convenience.
- Do not log private keys, full session secrets, or unredacted message bodies by default.
- Bug reports and diagnostics must default to redaction (hashes, paths, IPs, URLs, emails, display names).
- Plugin permissions stay capability-gated. No silent full-host mesh access for "examples".

## Gate 4: Scarcity and async

- Prefer event/handler and store-and-forward over blocking request/response UIs.
- Missing path: request path, allow propagate, surface recoverable error. Do not spin forever.
- Path and first-hop link waits use `path_utils.path_response_window` and `link.establishment_timeout`. Do not pin 15s (or any flat timer) for Nomad pages, RNCP, FileSync, LXST, or map fetches.
- Keep list APIs and announces slim. Do not ship multi-MB blobs in conversation lists.
- Large files use RNCP / attachments / explicit transfer tools, not chat text fields.

## Gate 5: Transport agnostic

- Application code uses RNS Destination / Link / Packet / LXMF APIs.
- Do not special-case WiFi vs LoRa vs TCP inside feature managers unless the feature is literally interface configuration.
- Interface selection belongs in Reticulum config and MeshChatX interface settings, not in message send hot paths.

## Gate 6: MeshChatX architecture fit

- Business rules in `meshchatx/src/backend/` managers, not dumped into `meshchat.py` routes.
- Identity-scoped state under `IdentityContext`. Switch must tear down cleanly.
- HTTP `/api/v1/*` for local UI. Mesh peers do not become REST clients of MeshChatX.
- New pages: route, nav/tools registry, i18n, toasts, tests (see `page-toast-tests`).
- New plugin managers/hooks: update `KNOWN_MANAGERS` / `KNOWN_HOOKS` and permission locale strings.

## Anti-patterns (do not ship)

| Anti-pattern                                         | Do this instead                                            |
| ---------------------------------------------------- | ---------------------------------------------------------- |
| `fetch('https://api...')` required to send a message | LXMF send via local router                                 |
| Store peer as `host:port`                            | Store destination hash + aspect                            |
| Spinner until ACK or fail hard                       | Outbound state machine + propagation                       |
| JSON status blob every second on LoRa                | Announce sparingly, encode intent densely                  |
| Global singleton cache of all identities' inboxes    | Per-identity DB and managers                               |
| New mesh app on `lxmf.delivery`                      | Dedicated aspect + link/request or LXMF only if it is mail |
| Debug dump with private key paths and full hashes    | Redacted export with user toggles                          |

## Review checklist (paste into PR / finish notes)

- [ ] Works with clearnet disabled / privacy mode on for mesh-critical paths
- [ ] Addresses destination hash + aspect
- [ ] Survives delay, missing path, and identity switch
- [ ] Payload size justified for constrained links
- [ ] No new unauthenticated mutating HTTP/WS surface
- [ ] No cross-identity leakage
- [ ] Tests cover success and recoverable failure
- [ ] Mesh/identity/auth changes cite matching EECT scenario ids under `tests/backend/eect/`

## Key references

- https://reticulum.network/manual/zen.html
- `.agents/conventions/reticulum-zen.md`
- `.agents/skills/reticulum-stack/SKILL.md`
- `.agents/overview.md`
- `docs/en/architecture.md`
- `docs/en/messaging.md`
- `docs/en/rns-link-api.md`
- `docs/en/identity-and-security.md`
