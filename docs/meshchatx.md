# MeshChatX Architecture and Design

MeshChatX is a very heavily customized fork of Reticulum-Meshchat, it is vastly different under the hood.

## Goals and Constraints

- Keep a local-first runtime model that works on desktop and headless systems.
- Preserve Reticulum and LXMF semantics while improving UX and operational tooling.
- Support multi-identity usage in one runtime without cross-identity data leakage.
- Keep the backend and frontend independently testable.
- Run in constrained environments (single board devices, containers, AppImage/desktop).

## System Overview

At a high level, MeshChatX is a single-process Python service that:

- initializes identity-specific context and persistent state,
- exposes HTTP API and WebSocket endpoints for the frontend,
- serves the built frontend assets from a local public directory,
- manages LXMF/Reticulum interactions and higher-level features.

The frontend is a SPA built with Vite and mounted in the same runtime context as the API.

## Runtime Topology

### Backend Runtime

- Main entrypoint: `meshchatx/meshchat.py` (orchestration). Shared helpers live in `meshchatx/src/path_utils.py`, `meshchatx/src/ssl_self_signed.py`, and `meshchatx/src/env_utils.py`; `meshchat.py` re-exports them for compatibility.
- Web stack: `aiohttp` + `aiohttp_session`
- Realtime channel: WebSocket endpoints for UI updates and control flows
- Transport/security: HTTPS by default, optional HTTP, optional custom cert paths

### Frontend Runtime

- Source tree: `meshchatx/src/frontend`
- Build output: `meshchatx/public`
- Served by backend static routing
- Uses API + WebSocket for state hydration and live updates

### Optional Desktop Runtime

- Electron packaging/build scripts at repository root
- Backend binaries/resources are bundled for packaged desktop artifacts

## Core Backend Design

### 1) Application Shell

`ReticulumMeshChat` in `meshchatx/meshchat.py` is the orchestration layer. It owns:

- server lifecycle,
- route registration,
- identity context switching and teardown,
- shared process-level concerns (logging, crash recovery wiring, health checks).

It intentionally centralizes operational control so runtime state changes happen in a predictable order.

### 2) Identity-Scoped Context Model

`IdentityContext` in `meshchatx/src/backend/identity_context.py` encapsulates state for one identity:

- storage path rooted at `storage/identities/<identity_hash>/`,
- identity-local SQLite DB,
- identity-local LXMF router state,
- manager instances (messages, announces, docs, map, forwarding, tools, and more).

This boundary prevents accidental cross-identity writes and keeps teardown deterministic.

### 3) Manager-Centric Domain Logic

Feature logic is delegated to dedicated backend modules under `meshchatx/src/backend`:

- message handling and routing,
- announce management and trimming/limits,
- docs, maps, page nodes, telemetry, interfaces,
- forwarding aliases and propagation synchronization,
- utility handlers for RN-specific tooling.

The design intent is to keep transport/runtime orchestration in `meshchat.py` and business/domain behavior in dedicated managers. Optional **RNS log level** is configured with **`--rns-log-level`** or **`MESHCHAT_RNS_LOG_LEVEL`** (CLI overrides env when both are set).

### 4) Persistence Layer

- Storage engine: SQLite
- Access style: explicit SQL-oriented data access layer (no heavyweight ORM)
- Schema migration and integrity checks are integrated into startup and context setup.

The project favors predictable SQL behavior and explicit migration control, which helps with compatibility and debugging on diverse platforms.

## API and Realtime Design

### HTTP API

- Implemented as explicit `aiohttp` routes in `meshchat.py`
- Includes app status, auth, messaging, interfaces, docs/tools, and maintenance endpoints
- Static assets are served from the frontend build output directory

### WebSockets

- Used for low-latency frontend state updates
- Keeps UI responsive for message state transitions and live network events

### Session/Auth Flow

- Cookie sessions via encrypted storage
- Auth and access-attempt tracking integrated with IP/User-Agent aware controls
- Debug endpoints provide visibility into logs and access-attempt records

This is also very well tested, but I still would not recommend exposing MeshChatX to the internet.

## Security Model

MeshChatX defaults toward secure local operation:

- HTTPS/WSS enabled by default.
- Self-signed cert generation if identity-local cert files are absent.
- Optional custom cert/key pair when deployment needs managed TLS material.
- CORS and CSP
- Session encryption and defensive middleware.
- Access attempt persistence plus lockout/rate limiting strategy (when auth enabled).

Since its HTTPS/WSS other local apps cannot sniff the traffic as easily.

## Build and Packaging Strategy

MeshChatX supports multiple deployment forms from one source tree:

- source/development execution,
- Python package and wheel distribution,
- container images,
- Electron desktop builds for major platforms.

The design uses a shared backend codebase and frontend build artifacts so feature behavior remains consistent across packaging targets.

## Operations and Reliability

Reliability features include:

- crash recovery integration,
- startup integrity/database health checks,
- backup/restore and snapshot support,
- explicit teardown flows for multi-context and forwarding resources,
- status endpoint for orchestration and container probes.

## Extensibility Points

The most practical extension points today are:

- new API routes in backend routing sections,
- new manager modules under `meshchatx/src/backend`,
- frontend page/component additions wired through existing router/state patterns,
- new config surface through CLI flags + environment variables,
- schema extension through the existing migration/versioning approach.

When adding features, prefer:

- identity-scoped state over global mutable state,
- explicit migration/version changes for DB schema updates,
- endpoint-level tests plus focused manager unit tests.
