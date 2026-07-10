# Architecture and design

MeshChatX is a heavily extended fork of Reticulum MeshChat. The goals below shaped how the codebase is organized.

## Design goals

- Keep a local-first runtime that works on desktop, mobile, containers, and single-board computers.
- Preserve Reticulum and LXMF semantics while improving usability and operational tooling.
- Support multiple identities in one process without cross-identity data leakage.
- Keep the Python backend and Vue frontend independently testable.
- Run in constrained environments with predictable SQLite behaviour.

Mesh features should follow Reticulum’s post-IP design patterns (portable identity hashes, announces, store-and-forward, transport-agnostic APIs, scarce payloads). Agent and contributor gates live in `docs/agents/conventions/reticulum-zen.md` and `docs/agents/skills/reticulum-design-gates/SKILL.md`, derived from the [Zen of Reticulum](https://reticulum.network/manual/zen.html).

## Process overview

One Python process owns the web server, Reticulum stack, and all per-identity managers. The Vue frontend is static assets served from `meshchatx/public/` after a Vite build.

```
ReticulumMeshChat (meshchat.py)
    |
    +-- HTTP routes (/api/v1/*, static files)
    +-- WebSocket (/ws, /ws/telephone/audio)
    +-- IdentityContext (per active identity)
    |       +-- SQLite via database layer
    |       +-- LXMRouter
    |       +-- TelephoneManager (LXST)
    |       +-- Domain managers (messages, map, docs, RRC, ...)
    +-- Shared Reticulum instance (~/.reticulum by default)
```

Optional **Electron** wraps the same backend binary and loads the UI from the local HTTPS server.

## Application shell

`ReticulumMeshChat` in `meshchatx/meshchat.py` is the orchestration layer. It registers routes, starts and stops identity contexts, wires crash recovery, and coordinates shared process concerns.

Path helpers live in `meshchatx/src/path_utils.py`, `ssl_self_signed.py`, and `env_utils.py`. `meshchat.py` re-exports them for compatibility.

## Identity-scoped context

`IdentityContext` in `meshchatx/src/backend/identity_context.py` encapsulates everything tied to one cryptographic identity:

- Storage under `storage/identities/<identity_hash>/`
- Identity-local SQLite database (schema version tracked in migrations)
- LXMF router state and propagation directories
- Manager instances for messages, announces, docs, maps, forwarding, bots, RRC, Nomad page nodes, and more

Switching identities tears down the old context and loads another. Global mutable state that could leak between identities is avoided by design.

## Manager-centric domain logic

Feature behaviour lives in modules under `meshchatx/src/backend/`. Examples include message handling, announce trimming, documentation, maps, page nodes, telemetry, interfaces, forwarding aliases, and RN-specific tool handlers.

`meshchat.py` should stay focused on transport and lifecycle. Business rules belong in managers where they can be unit tested.

## Persistence

- **Engine:** SQLite with explicit SQL and migrations (no ORM).
- **Schema:** Versioned migrations run during startup and identity setup.
- **Backups:** Automatic and manual database backups under `database-backups/`.
- **Recovery:** `--auto-recover`, emergency mode, and Electron crash UI can restore from backups.

## HTTP API

Routes are registered explicitly on the aiohttp application. Categories include:

- Application status and configuration
- Authentication and session management
- LXMF messaging and conversations
- Telephone and voicemail
- Interfaces and Reticulum configuration
- Nomad Network and page nodes
- RRC client and server
- Tools (ping, RNPath, RNCP, RNSH, translator, bots)
- Documentation and maintenance

The frontend uses `fetch` via `apiClient.js` with CSRF tokens on mutating requests.

## WebSockets

The UI connects to `/ws` for low-latency updates. Event types include new LXMF messages, identity switches, telephone state, RRC activity, Nomad download progress, RNCP transfers, and plugin events. Handlers are registered in `wsEventRegistry.js` and dispatched through `wsEventBridge.js`.

Audio calls can use `/ws/telephone/audio` for browser-side codec bridging.

## Security model

MeshChatX defaults toward secure local operation:

- HTTPS and WSS enabled by default.
- Self-signed certificates generated per identity when custom PEM files are absent.
- Optional HTTP basic authentication (`--auth`).
- Encrypted session cookies via `aiohttp_session`.
- CORS, CSP, and defensive middleware on HTTP responses.
- Access attempt logging with lockout when auth is enabled.

The project includes extensive automated tests around auth and sessions. Even so, exposing MeshChatX directly to the public internet is not recommended without additional hardening.

Password reset is available with `--reset-password` or `MESHCHAT_RESET_PASSWORD=true`, which clears the stored bcrypt hash so you can set a new password in the UI.

## Build and packaging

One source tree produces:

- Development runs via `uv run python -m meshchatx.meshchat`
- Python wheels with bundled `public/` assets
- Container images (Dockerfile and hardened variants)
- Electron builds for Windows, macOS, and Linux
- Android APK via Chaquopy

Frontend build output always lands in `meshchatx/public/` so runtime behaviour matches across targets.

## Reliability features

- Crash recovery integration in Electron and backend startup checks
- Database integrity verification
- Backup, restore, and snapshot APIs
- Explicit teardown when switching identities or shutting down forwarding resources
- Health and status endpoints suitable for container probes

## Extensibility

MeshChatX supports plugins with separate frontend and backend runtimes:

- **Contribution registries** under `meshchatx/src/frontend/js/registries/` for navigation, tools, commands, settings, and WebSocket events.
- **Frontend plugins** run in dedicated Workers (`PluginHost.js`) with declarative UI slots.
- **Backend WASM plugins** run in wasmtime with fuel metering and capability-gated host functions.
- **Backend Python plugins** (`backend.type: "python"`) run in-process with a permission-checked host (`log`, managers, storage, network flag).
- **WASM bundles** embed manifest/files/signature in custom sections and unpack on install.
- **Sideband-compatible loader** optionally `exec`s flat `*.py` plugins with `PLUGIN_COMMAND` LXMF dispatch.
- **Security core** verifies RSG signatures, trusted publishers, integrity hashes, and heuristic findings.
- **HTTP API** under `/api/v1/plugins/*` and `/api/v1/sideband-plugins/*` for install, enable, invoke, trust, and Sideband config.

Practical extension paths today:

- Plugin manifests with `contributes` and `permissions` blocks
- New API routes and manager modules
- Frontend pages wired through registries
- New settings via `ConfigManager` and CLI or environment variables
- Database schema changes through migrations
- Generic RNS Link transport over WebSocket (`rns.link.*`) for external consoles and plugins (see **RNS Link API**)

Granted plugin manager capabilities include `destinationPath.read`, `debugLog.read`, `bugReport.*`, and `rnsLink.open` / `identify` / `request` / `send` / `close`. Hooks include `announce.received` and `rns.link.event`. Storage (`storage:isolated`) and outbound HTTP (`network:fetch`) are also grantable; install preview scans plugin files for external URLs and stores the user-selected grant subset.

When adding features, prefer identity-scoped state, explicit migrations, endpoint tests, and narrowly declared plugin permissions.

## NomadNet and Mesh Server

The Nomad browser and Mesh Server (page nodes) share a rendering pipeline for Micron, Markdown, plain text, and sanitised HTML. Authoring rules are documented in **NomadNet page formats**.

## Related reading

- **Getting started** for UI navigation and first steps.
- **LXMF messaging**, **Audio calls**, and **Reticulum interfaces** for feature behaviour.
- The **Reticulum** tab in Documentation for protocol reference.
