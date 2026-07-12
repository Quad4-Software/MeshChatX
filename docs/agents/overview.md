# MeshChatX agent overview

Project brief for automated agents and contributors.
Conventions and task skills live under `docs/agents/`. This file is the durable source of truth for architecture and invariants.

## What this project is

Reticulum MeshChatX is a local-first mesh communications client on the Reticulum Network Stack.
It is an independent fork of Reticulum MeshChat and is not affiliated with the upstream project.

Core protocols:

- **Reticulum (RNS)** - identities, paths, interfaces, encrypted transport
- **LXMF** - messaging, attachments, propagation nodes
- **LXST** - audio calls and telephony

One Python process owns the web server, Reticulum stack, and per-identity managers.
The Vue frontend is static assets served from `meshchatx/public/` after a Vite build.
Electron and Android wrap the same backend.

Website: [meshchatx.com](https://meshchatx.com)
Source: [github.com/Quad4-Software/MeshChatX](https://github.com/Quad4-Software/MeshChatX)

## Design goals (do not violate casually)

- Local-first. Works on desktop, mobile, containers, and SBCs.
- Preserve Reticulum / LXMF / LXST semantics while improving UX and ops tooling.
- Multiple identities in one process without cross-identity data leakage.
- Python backend and Vue frontend independently testable.
- Predictable SQLite behaviour in constrained environments.
- Prefer identity-scoped state, explicit migrations, and narrowly declared plugin permissions.

## Reticulum Zen gates (mesh work)

MeshChatX sits on Reticulum. Agents must not invent cloud-era or IP-era designs for mesh features.

- Philosophy: [Zen of Reticulum](https://reticulum.network/manual/zen.html)
- Conventions: `docs/agents/conventions/reticulum-zen.md`
- Checklist skill: `docs/agents/skills/reticulum-design-gates/SKILL.md`
- Cursor always-on rule: `.cursor/rules/reticulum-zen-gates.mdc`

Short form: no mandatory cloud center, address destination hashes, assume hostile links, design for scarcity and delay, keep code transport-agnostic, keep identity state scoped.

## Runtime shape

```
Browser / Electron / Android WebView
    |
    |  HTTPS REST /api/v1/*  and  WSS /ws  (+ /ws/telephone/audio)
    v
ReticulumMeshChat (meshchatx/meshchat.py)
    |
    +-- HTTP routes and static public/
    +-- WebSocket event fan-out
    +-- IdentityContext (active identity only)
    |       +-- SQLite (database.db under identity storage)
    |       +-- LXMRouter and message managers
    |       +-- TelephoneManager (LXST)
    |       +-- Domain managers (map, docs, RRC, bots, ...)
    +-- Shared Reticulum instance (default ~/.reticulum)
```

Critical lifecycle facts:

- HTTP can bind before RNS/identity finish starting. `/api/v1/status` reports `starting` / `ok` / `failed` with `stage` and `network_ready`.
- CLI one-shots (`--self-check`, backup/restore helpers) still initialize synchronously.
- Switching identities tears down the old `IdentityContext` and loads another. Do not stash identity-specific state in process globals.

## Repository layout

| Path                      | Role                                      |
| ------------------------- | ----------------------------------------- |
| `meshchatx/meshchat.py`   | Orchestration, HTTP/WS routes, CLI        |
| `meshchatx/src/backend/`  | Managers, DB, security, Landlock, plugins |
| `meshchatx/src/frontend/` | Vue 3 UI, locales, registries, helpers    |
| `meshchatx/public/`       | Built frontend assets consumed at runtime |
| `electron/`               | Desktop shell around local HTTPS backend  |
| `android/`                | WebView + Chaquopy Python bridge          |
| `tests/backend/`          | pytest                                    |
| `tests/frontend/`         | vitest                                    |
| `tests/e2e/`              | Playwright                                |
| `docs/en/`                | In-app / shipped English docs             |
| `vendor/`                 | Vendored deps (for example LXMFy)         |
| `Taskfile.yml`            | Preferred command entrypoints             |
| `docs/agents/`            | Agent guidance (this tree)                |
| `AGENTS.md`               | Short pointer to `docs/agents/`           |

Business rules belong in backend managers under `meshchatx/src/backend/`.
Keep `meshchat.py` focused on transport and lifecycle when possible.

## Tooling and versions

- Python `>=3.11` (CI commonly runs 3.14)
- Node.js `>=24`, pnpm from `package.json` `packageManager`
- UV for Python deps
- Task for common workflows

Prefer Task targets over inventing one-off scripts:

```bash
task install
task format
task lint
task test:quick
task test:backend
task test:frontend
task test:e2e
task run
task dev
```

Optional RNS/rngit tooling (requires mesh reachability, can sometimes be significantly slower than PyPI):

```bash
task deps:backend:rns
task docs:rns
```

Useful focused commands:

```bash
uv run pytest tests/backend/test_<name>.py -q --tb=short
pnpm exec vitest run tests/frontend/<Name>.test.js
pnpm exec eslint <file> --fix
uv run python -m meshchatx.meshchat --self-check
```

## Storage and identity model

Default storage root: `./storage` (override with `--storage-dir` / `MESHCHAT_STORAGE_DIR`).
Android may prefer external app files storage.

Per identity:

```
storage/identities/<identity_hash>/
  identity                 # private key bytes
  metadata.json            # display name, icon, cached addresses
  database.db              # SQLite (WAL files may exist)
  database-backups/        # zip backups
  snapshots/               # named snapshots
  ssl/                     # per-identity cert/key when using defaults
  ...                      # LXMF dirs, caches, sqlite-tmp, etc.
```

Shared outside identity storage:

- Reticulum config: `~/.reticulum` by default (`--reticulum-config-dir` / `MESHCHAT_RETICULUM_CONFIG_DIR`)
- Interfaces and transport settings live with Reticulum, not only in the identity DB

### Identity key restore vs database restore

These are different operations. Do not conflate them in UI copy or code paths.

| Goal                                          | Where                              | Artifact / API                                         |
| --------------------------------------------- | ---------------------------------- | ------------------------------------------------------ |
| Restore private key only                      | Tutorial step 2, Identities import | `POST /api/v1/identity/restore`                        |
| Restore LXMF history, settings, identity tree | About → Restore from File, CLI     | `POST /api/v1/database/restore`, `--restore-db` `.zip` |

Identity export download should use a real extension such as `identity.bin`.
File pickers for keys should accept `.bin`, `.key`, `.identity`, `application/octet-stream`, and `*/*`.
Database restore pickers stay `.zip`.

## Persistence rules

- Engine: SQLite with explicit SQL and versioned migrations (no ORM).
- Schema changes go through migrations in the database schema layer.
- Backups and snapshots are first-class recovery tools. Prefer restore APIs over hand-editing DB files.
- Conversation list / sidebar queries must stay slim. Truncate content previews. Derive attachment flags in SQL. Do not ship multi-MB `fields` blobs in list endpoints.
- Worker-thread DB connections must apply the same pragmas as the main connection via `DatabaseProvider` (especially `temp_store`).

## Landlock and Linux sandboxing

On Linux, MeshChatX can apply a Landlock filesystem sandbox after startup.
Control with `MESHCHAT_LANDLOCK` (`1` force on, `0` force off, unset = auto when kernel supports it).

Critical SQLite interaction:

- Under Landlock, `PRAGMA temp_store=FILE` can break complex conversation queries with `unable to open database file`.
- Default worker connections to `temp_store=MEMORY`.
- Memory-pressure mode may shrink cache/mmap. While Landlock is active, keep MEMORY temp.
- Without Landlock, FILE temp plus a storage-local `sqlite-tmp` TMPDIR is acceptable.

Landlock apply is process-wide and one-shot. Tests that enable it must run in a subprocess.

Also see `docs/en/platform-guides/linux-sandbox.md` for Firejail / Bubblewrap host examples.

## Security model (critical)

Defaults aim at secure local operation:

- HTTPS and WSS on by default (self-signed certs per identity when custom PEMs absent)
- Optional HTTP auth (`--auth` / `MESHCHAT_AUTH=true`)
- CSRF on mutating HTTP requests
- Encrypted session cookies
- CORS / CSP / defensive HTTP middleware
- Access-attempt logging and lockout when auth is enabled
- IP allowlisting available via app security settings
- Privacy mode can block outbound clearnet HTTP from app features (does not stop Reticulum mesh traffic)

Do not recommend exposing MeshChatX directly on the public internet without extra hardening.
Prefer bind `127.0.0.1`, HTTPS, and auth if other local users share the host.

Sensitive config changes (for example auth enable / password hash) must use CSRF-protected HTTP endpoints, not unrestricted WebSocket mutators.

Password reset: `--reset-password` or `MESHCHAT_RESET_PASSWORD=true` clears the stored hash so a new password can be set in the UI.

### Plugins

Plugins are powerful and partially sandboxed. Treat install/enable paths as security-sensitive.

- Frontend plugins run in Workers with capability grants
- Backend WASM plugins use wasmtime with fuel / capability gates
- Backend Python plugins and Sideband loaders are higher risk and permission-gated / danger-switched
- Invalid RSG signatures hard-block install
- Tampered installed trees should disable as integrity failures
- Disable all plugins with `--disable-plugins` / `MESHCHAT_DISABLE_PLUGINS=true`

## HTTP and WebSocket surface

- REST under `/api/v1/*`
- Frontend uses `window.api` / `apiClient.js` with CSRF on mutating calls
- WebSocket `/ws` for live events (messages, identity switch, telephone, RRC, Nomad downloads, plugins, RNS link events)
- Typed WS handlers live in frontend registries (`wsEventRegistry` / `wsEventBridge`)
- Generic RNS Link API over WS (`rns.link.open|identify|request|send|close` and `rns.link.event`) for external tools and plugins. See `docs/en/rns-link-api.md`.

When identity/network is not ready, prefer **503** with a retryable message over opaque **500** for temporary DB/startup failures.

## Frontend conventions

- Vue 3 Options API is the dominant style. Match the file you edit.
- Routes are hash-based (for example `#/messages`).
- New top-level pages need: route in `main.js`, nav/tools entry when discoverable, i18n keys, tests.
- User-visible strings go through locale files (`meshchatx/src/frontend/locales/en.json` at minimum).
- User-visible action outcomes use `ToastUtils`.
- Do not use `_`-prefixed keys in Vue `data()` (`vue/no-reserved-keys`).
- Contribution registries drive nav, tools, commands, settings sections, and WS events. Prefer extending registries over hardcoding one-off shell wiring.

## Android specifics

- UI is a WebView. Backend runs via Chaquopy.
- File chooser: bare extension tokens like `.identity` are not valid MIME types for `Intent.EXTRA_MIME_TYPES`. Map them to `application/octet-stream` / `*/*`.
- Set multi-select only when the WebView chooser mode requests it.
- Storage setup (internal vs external) can create a fresh-looking install if the user picks a different location than previous data.
- External http(s) links should open in the system browser, not navigate the WebView away from the app.

## Important environment variables and flags

Common overrides (CLI flags usually mirror these):

| Variable / flag                                            | Purpose                                          |
| ---------------------------------------------------------- | ------------------------------------------------ |
| `MESHCHAT_HOST` / `--host`                                 | Bind address (default `127.0.0.1`)               |
| `MESHCHAT_PORT` / `--port`                                 | Bind port (default `8000`)                       |
| `MESHCHAT_HEADLESS` / `--headless`                         | Do not auto-launch a browser                     |
| `MESHCHAT_STORAGE_DIR` / `--storage-dir`                   | App storage root                                 |
| `MESHCHAT_RETICULUM_CONFIG_DIR` / `--reticulum-config-dir` | Reticulum config dir                             |
| `MESHCHAT_PUBLIC_DIR` / `--public-dir`                     | Frontend assets dir                              |
| `MESHCHAT_AUTH` / `--auth`                                 | Enable web auth                                  |
| `MESHCHAT_NO_HTTPS` / `--no-https`                         | HTTP instead of HTTPS                            |
| `MESHCHAT_SSL_CERT` + `MESHCHAT_SSL_KEY`                   | Custom TLS PEM pair (both required)              |
| `MESHCHAT_IDENTITY_FILE` / `BASE32` / `BASE64`             | Seed identity from key material                  |
| `MESHCHAT_AUTO_RECOVER` / `--auto-recover`                 | Attempt DB recovery on startup                   |
| `MESHCHAT_EMERGENCY` / `--emergency`                       | Emergency mode (limited operation)               |
| `MESHCHAT_RESET_PASSWORD` / `--reset-password`             | Clear password hash                              |
| `MESHCHAT_DISABLE_PLUGINS` / `--disable-plugins`           | Disable plugin system                            |
| `MESHCHAT_LANDLOCK`                                        | `1` / `0` / unset auto                           |
| `MESHCHAT_SELF_CHECK` / `--self-check`                     | Run diagnostics and exit                         |
| `MESHCHAT_MEMORY_DIAG` / `--memory-diag`                   | tracemalloc diagnostics                          |
| `MESHCHAT_DISABLE_CSRF`                                    | Dangerous. Tests/dev only                        |
| `MESHCHAT_SKIP_STORAGE_LOCK`                               | Dangerous. Avoid overlapping instances carefully |
| `MESHCHAT_RNS_LOG_LEVEL`                                   | RNS log verbosity                                |

Restore helpers:

```bash
meshchatx --restore-db /path/to/backup.zip
```

## Testing expectations

- Backend change → update `tests/backend/`
- Frontend change → update `tests/frontend/`
- API contract / route list fixtures may need updates when routes change
- Prefer focused suites in agent loops. Full `task test` is heavy.
- Avoid piping long pytest runs through `| tail` in automation shells (can hang the harness).
- Landlock-enable tests must use a subprocess.
- Long-running soak / some notification suites can hang. Use timeouts and isolate them unless explicitly requested.
- Self-check and CI matrices cover cross-platform boot, storage lock fallbacks, and critical HTTP/WS probes. Do not weaken those without cause.

## Licensing and contributions

- Prefer existing per-file SPDX headers. Project-owned files are typically `0BSD`.
- Upstream-derived files may be MIT or dual-marked. Preserve obligations.
- Patch-oriented contribution flow is documented in `CONTRIBUTING.md` (LXMF patch submission is first-class for some contributors).
- Generative AI policy in `CONTRIBUTING.md` requires disclosure and human review. Do not submit unreviewed bulk-generated churn.

## Agent hard rules

1. No emojis in code, markdown, or docs you write for this repo.
2. No TODO / FIXME noise comments.
3. No emdashes or semicolons in comments or docs you write.
4. Do not create markdown docs unless asked (except agent guidance under `docs/agents/` when requested).
5. Do not commit or push unless the user asks.
6. Do not generate exploit PoCs, malware, or attack tooling.
7. Prefer minimal diffs. Match nearby style.
8. Do not invent install/run flows when Taskfile already covers them.
9. Mesh-facing designs must pass Zen / architecture gates (`reticulum-zen.md` / `reticulum-design-gates`).

## High-risk change checklist

Before finishing work in these areas, verify the matching invariants:

1. **Identity import / tutorial** - key-only vs zip restore copy is correct, picker accepts real exports, activate-on-finish / skip paths do not orphan imports.
2. **Conversations / notifications DB** - slim queries, MEMORY temp under Landlock, 503 on retryable SQLite errors.
3. **Auth / CSRF / WS config** - no new unauthenticated mutating surfaces, no sensitive settings over open WS mutators.
4. **Plugins** - permissions declared, install preview/consent preserved, signatures/integrity not bypassed.
5. **Android bridges** - MIME mapping, storage paths, and WebView navigation guards remain correct.
6. **Identity switch** - no cross-identity leakage via caches, routers, or global singletons.
7. **Migrations** - schema version bump and upgrade path tested.

## Where to read next

- `docs/agents/conventions/reticulum-zen.md` - Zen of Reticulum hard gates
- `docs/agents/skills/reticulum-design-gates/SKILL.md` - mesh design checklist
- `docs/en/architecture.md` - design and process overview
- `docs/en/identity-and-security.md` - identities, auth, privacy, backups
- `docs/en/getting-started.md` - UI map and first-run workflow
- `docs/en/rns-link-api.md` - generic RNS Link WebSocket API
- `docs/en/platform-guides/linux-sandbox.md` - Firejail / Bubblewrap
- `docs/en/messaging.md` - LXMF behaviour
- `CHANGELOG.md` - version-facing behaviour changes
- `CONTRIBUTING.md` - patch and AI disclosure policy

## Agent guidance index

- `docs/agents/README.md` - index of conventions and skills
- `docs/agents/conventions/` - surface-specific rules including Reticulum Zen
- `docs/agents/skills/` - focused workflows including reticulum-design-gates, pages, registries, identity restore/switch, Landlock/SQLite, migrations/backups, auth/CSRF/WS, plugins, RNS Link API, deferred startup, Electron packaging, Android bridge, and test loop
