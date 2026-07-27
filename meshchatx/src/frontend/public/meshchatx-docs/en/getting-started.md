# Getting started with MeshChatX

MeshChatX is a local-first mesh communications client built on the Reticulum Network Stack. It combines direct messaging over LXMF, voice calls over LXST, NomadNet page browsing, relay chat, maps, and a large set of Reticulum utilities in one application you can run on a desktop, a headless server, or a mobile device.

MeshChatX is an independent fork of [Reticulum MeshChat](https://github.com/liamcottle/reticulum-meshchat). It is not affiliated with the upstream project. The website is [meshchatx.com](https://meshchatx.com). Source and releases live on [GitHub](https://github.com/Quad4-Software/MeshChatX).

## What you need to know first

Reticulum is the mesh networking layer. It handles identities, paths, interfaces, and encrypted transport between nodes. LXMF is the messaging protocol MeshChatX uses for conversations, attachments, and propagation. LXST is the telephony layer used for audio calls.

MeshChatX does not replace Reticulum. It runs Reticulum inside a Python process, exposes a web UI, and stores your per-identity data locally in SQLite.

## How the application is laid out

When you open MeshChatX you work inside a single-page web interface. The sidebar lists the main areas of the app. The **Tools** page groups diagnostics and utilities. **Settings** holds per-identity configuration. **Identities** lets you create or switch between separate cryptographic identities.

Typical first-day workflow:

1. Install MeshChatX using a method that fits your device. See **Installation and setup**.
2. Open the web UI. The default address is `https://127.0.0.1:8000` when HTTPS is enabled.
3. Go to **Interfaces** and add a way to reach the mesh. A TCP client, community interface suggestion, or LoRa RNode are common starting points.
4. Wait for paths and announces to populate. Peers appear in the announces list and in feature-specific views.
5. Open **Messages** to start an LXMF conversation, or **Nomad Network** to browse a page node.

## Runtime shape

MeshChatX ships as one Python service that serves both the API and the built frontend assets.

```
Browser or Electron window
    |
    v
Vue 3 frontend (hash routes such as #/messages)
    |
    |  REST under /api/v1/*  and  WebSocket at /ws
    v
meshchatx/meshchat.py (aiohttp server)
    |
    +--> SQLite database (per identity)
    +--> LXMF router and message store
    +--> LXST telephone (when enabled)
    +--> Reticulum stack (interfaces, paths, announces)
```

The same backend code powers Docker images, Python wheels, Linux packages, Electron desktop builds, and the Android APK. Packaging differs. Behaviour is intended to stay consistent.

In a regular browser (including headless or LAN installs), MeshChatX may register a service worker that caches hashed UI assets and the app shell so repeat loads are faster and a hard refresh can still show the boot splash while the local backend restarts. Mesh messaging, identity, and API data still require the Python backend. Electron does not use this service worker path.

## Main areas of the UI

| Area               | Route                 | Purpose                                               |
| ------------------ | --------------------- | ----------------------------------------------------- |
| Messages           | `/messages`           | LXMF direct messaging, folders, attachments           |
| Audio calls        | `/call`               | LXST voice calls and voicemail                        |
| Contacts           | `/contacts`           | Telephone contacts and call-related entries           |
| Relay chat         | `/relay-chat`         | RRC hubs and rooms (when enabled in settings)         |
| Nomad Network      | `/nomadnetwork`       | Browse remote NomadNet pages and files                |
| Map                | `/map`                | OpenLayers map, offline tiles, telemetry              |
| Archives           | `/archives`           | Versioned snapshots of Nomad pages                    |
| Tools              | `/tools`              | Ping, path tools, RNCP, bots, documentation, and more |
| Interfaces         | `/interfaces`         | Add and manage Reticulum interfaces                   |
| Network visualiser | `/network-visualiser` | Graph view of mesh topology                           |
| Blocked            | `/blocked`            | Blocked destinations                                  |
| Settings           | `/settings`           | Theme, language, LXMF, telephone, security            |
| Identities         | `/identities`         | Create, import, or switch identities                  |
| Documentation      | `/documentation`      | MeshChatX guides and the Reticulum manual             |

Relay chat appears only when `rrc_enabled` is turned on in settings. When enabled, the Relay chat icon can show a red mention count. Messages shows unread conversation count. Calls shows unread missed-call count.

## Documentation in the app

The **Documentation** page has two tabs.

**MeshChatX** shows the guides in this bundle. They are markdown files synced from the `docs/` directory in the repository and rendered offline inside the app.

**Reticulum** shows the upstream Reticulum manual as pre-built HTML. It is bundled at build time. You can upload a newer manual ZIP if you need a different version.

Use the search bar to query both sets at once. MeshChatX guide text is currently available in English. The Reticulum manual body is English. Localized landing pages exist for several languages on the Reticulum tab.

## Storage locations

| Data                  | Typical path (CLI default)                         |
| --------------------- | -------------------------------------------------- |
| MeshChatX app data    | `./storage` (or `--storage-dir` / `MESHCHAT_STORAGE_DIR`) |
| Reticulum config      | `~/.reticulum` (or `--reticulum-config-dir` / `MESHCHAT_RETICULUM_CONFIG_DIR`) |
| Portable bundle       | `<data-dir>/storage` and `<data-dir>/.reticulum` when using `--data-dir` / `MESHCHAT_DATA_DIR` |
| Desktop Electron data | `~/.reticulum-meshchatx` and `~/.reticulum` unless overridden at launch |
| Per-identity database | `<storage>/identities/<identity_hash>/database.db` |
| Docker volume         | `meshchatx-config` mounted at `/config`            |

Legacy upstream data may still exist under `~/.reticulum-meshchat/`. Migration tooling can move you to the MeshChatX layout.

## Where to go next

- **Installation and setup** covers Docker, wheels, desktop packages, and development builds.
- **Architecture and design** explains backend managers, identity scoping, and the API model.
- **LXMF messaging** and **Audio calls** describe day-to-day communication features.
- **Reticulum interfaces** explains how your node joins the mesh.
- Platform guides under **Platform guides** cover Raspberry Pi, Android Termux, Meta Quest, Linux sandboxing, and Windows AppContainer sandboxing.

For protocol-level detail, open the **Reticulum** tab in Documentation or visit the [Reticulum manual](https://reticulum.network/manual/) online.
