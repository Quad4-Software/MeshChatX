---
name: nomad-pages
description: NomadNet page browsing and Mesh Server page nodes (nomadnetwork.node, Micron, Markdown). Use when changing nomad routes, page_node manager, WS download, or allowed page formats.
---

# Skill: nomad-pages

NomadNet pages are Reticulum destinations with aspect nomadnetwork.node. MeshChatX browses remote nodes and can host local page nodes (Tools, Mesh Server). Local HTTPS is the control plane for this device. Remote nodes are not REST clients of MeshChatX.

User docs: docs/en/nomad-network.md, docs/en/nomadmesh-pages.md.

## When to use

- Nomad browser UI, downloads, or archives
- Page node create/start/stop, file upload, request handlers
- Micron (.mu), Markdown, plain text, or sanitised HTML rendering
- WS types that fetch or cache remote pages

Generic RNS Link transport for non-Nomad apps is rns-link-api, not this skill.

## Hosted nodes

- Manager: meshchatx/src/backend/page_node_manager.py
- Destination: meshchatx/src/backend/page_node.py (APP_NAME = "nomadnetwork")
- Storage: storage/identities/<hash>/page_nodes/<node_id>/
- HTTP: meshchatx/src/backend/http/routes/page_nodes.py
- Browse/download HTTP: meshchatx/src/backend/http/routes/nomad.py
- WS: meshchatx/src/backend/http/ws/handlers_nomad.py

Page-node files are a path jail. Follow path-jail-local-fs. The Mesh Server rejects disallowed extensions on upload (see NomadNet page formats).

Executable pages are a per-node opt-in. POSIX uses chmod +x. Windows stores names in the node config.json and runs the page via its shebang interpreter on PATH. Editing always returns file source, never script stdout.

## Formats

| Extension | Role                                                  |
| --------- | ----------------------------------------------------- |
| .mu     | Micron markup (NomadNet default)                      |
| .md     | Markdown                                              |
| .txt    | Plain text                                            |
| HTML      | Sanitised. Do not widen the sanitiser to run scripts. |

Announce display names parse through parse_nomadnetwork_node_display_name. Store toggles: announce_store_nomadnetwork_node in announce_manager.py.

## Gates

1. Address nodes by destination hash, not IP.
2. Downloads and WS mutators require an authenticated session when password auth is enabled (auth-csrf-ws-security).
3. Privacy mode blocks clearnet helpers around Nomad. Mesh page fetch over RNS stays allowed (privacy-mode-clearnet).
4. Tear down hosted destinations on identity switch.

## Verification

Prefer focused backend tests next to existing page-node / nomad tests, plus frontend tests when the browser UI changes.
