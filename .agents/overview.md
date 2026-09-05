# MeshChatX agent overview

Architecture and invariants. Conventions and skills: `.agents/README.md`.
Load this file when you need storage, security, env, or runtime shape. Prefer a skill for task work.

## Project

Local-first mesh client on Reticulum. Independent fork of Reticulum MeshChat (not affiliated).

| Stack piece | Role                                               |
| ----------- | -------------------------------------------------- |
| RNS         | identities, paths, interfaces, encrypted transport |
| LXMF        | messaging, attachments, propagation                |
| LXST        | audio calls / telephony                            |

One Python process owns HTTPS, Reticulum, and per-identity managers.
Vue assets: `meshchatx/public/` after Vite. Electron and Android wrap the same backend.

Site: https://meshchatx.com
Source: https://github.com/Quad4-Software/MeshChatX

Goals: local-first, correct RNS/LXMF/LXST semantics, multi-identity without leakage, testable Python + Vue, predictable SQLite, narrow plugin permissions.

## Mesh Zen

Do not invent cloud/IP-era designs for mesh features.

```
.agents/conventions/reticulum-zen.md
.agents/skills/reticulum-design-gates/SKILL.md
```

Always-on editor rule: `.cursor/rules/reticulum-zen-gates.mdc`.

## Runtime

```
Browser / Electron / Android WebView
  |  HTTPS /api/v1/*  and  WSS /ws  (+ /ws/telephone/audio)
  v
ReticulumMeshChat (meshchatx/meshchat.py)
  +-- http/ (middleware, routes/*, ws/*)
  +-- static public/
  +-- IdentityContext (active identity only)
  |     SQLite, LXMRouter, TelephoneManager, domain managers
  +-- Shared Reticulum (~/.reticulum by default)
```

- HTTP can bind before RNS/identity finish. `/api/v1/status` reports `starting` / `ok` / `failed` with `stage` and `network_ready`.
- CLI one-shots (`--self-check`, backup/restore) init synchronously.
- Identity switch tears down `IdentityContext`. No identity state in process globals.

## Repo layout

| Path                          | Role                                      |
| ----------------------------- | ----------------------------------------- |
| `meshchatx/meshchat.py`       | orchestration, CLI, lifecycle             |
| `meshchatx/src/backend/http/` | middleware, routes, WS                    |
| `meshchatx/src/backend/`      | managers, DB, security, Landlock, plugins |
| `.agents/module-ownership.md` | domain to code/tests map                  |
| `meshchatx/src/frontend/`     | Vue 3 UI                                  |
| `meshchatx/public/`           | built assets                              |
| `electron/`                   | desktop shell                             |
| `android/`                    | WebView + Chaquopy                        |
| `tests/backend/`              | pytest                                    |
| `tests/frontend/`             | vitest                                    |
| `tests/e2e/`                  | Playwright E2E                            |
| `tests/ui/`                   | Playwright UI + Lighthouse                |
| `docs/en/`                    | shipped user docs                         |
| `vendor/`                     | LXMFy, RNS FileSync                       |
| `Taskfile.yml`                | preferred commands                        |

Business rules live in managers under `meshchatx/src/backend/`. Keep `meshchat.py` on transport and lifecycle.

## Tooling

Python `>=3.11` (CI often 3.14). Node `>=24`. pnpm from `packageManager`. UV. Task.

```bash
task install
task format
task lint
task test:quick
task test:eect
task test:lv:l0
task test:backend
task test:frontend
task test:e2e
task test:ui:pages
task test:ui:lighthouse
task run
task dev
task debug
```

Optional mesh-side deps (slower, needs reachability):

```bash
task deps:backend:rns
task docs:rns
```

Focused:

```bash
uv run pytest tests/backend/test_<name>.py -q --tb=short
pnpm exec vitest run tests/frontend/<Name>.test.js
pnpm exec eslint <file> --fix
uv run python -m meshchatx.meshchat --self-check
```

## Storage and identity

Default root: `./storage` (`--storage-dir` / `MESHCHAT_STORAGE_DIR`). Android may use external app files.

```
storage/identities/<identity_hash>/
  identity                 # private key bytes
  metadata.json
  database.db              # WAL sidecars possible
  database-backups/
  snapshots/
  ssl/
  ...                      # LXMF dirs, caches, sqlite-tmp
```

Shared: Reticulum config `~/.reticulum` (`--reticulum-config-dir` / `MESHCHAT_RETICULUM_CONFIG_DIR`). Interfaces live with Reticulum, not only in the identity DB.

### Key restore vs database restore

Do not conflate these.

| Goal                    | Where                              | Artifact                                               |
| ----------------------- | ---------------------------------- | ------------------------------------------------------ |
| Private key only        | Tutorial step 2, Identities import | `POST /api/v1/identity/restore`                        |
| History + settings tree | About restore, CLI                 | `POST /api/v1/database/restore`, `--restore-db` `.zip` |

Key export extension: `identity.bin`. Key pickers: `.bin`, `.key`, `.identity`, `application/octet-stream`, `*/*`. DB restore pickers: `.zip` only.
Skill: `.agents/skills/identity-restore/SKILL.md`.

## Persistence

- SQLite, explicit SQL, versioned migrations (no ORM).
- Schema changes through the database schema layer.
- Prefer restore APIs over hand-editing DB files.
- Conversation list queries stay slim: truncate previews, attachment flags in SQL, no multi-MB `fields` in list endpoints.
- Worker DB connections use the same pragmas via `DatabaseProvider` (especially `temp_store`).

## Landlock

`MESHCHAT_LANDLOCK`: `1` on, `0` off, unset = auto when kernel supports.

| Fact             | Detail                                                                                   |
| ---------------- | ---------------------------------------------------------------------------------------- |
| SQLite           | Under Landlock, `temp_store=FILE` can yield `unable to open database file`. Keep MEMORY. |
| Memory pressure  | May shrink cache/mmap. Keep MEMORY temp while Landlock is active.                        |
| Without Landlock | FILE temp + storage-local `sqlite-tmp` TMPDIR is fine.                                   |
| Subprocess       | PATH tools outside allowed roots fail with Permission denied even if "detected".         |
| Allowed extras   | `~/.local/bin`, pipx, Argos under `~/.local/share/argos-translate`.                      |
| rnsh/rnx         | Prefer `python -m …`. rnsh uses storage-scoped HOME.                                     |
| Not covered      | Broken symlinks out of allowed trees, nvm-only tools, arbitrary `location_cmd`.          |
| Tests            | Apply Landlock only in a subprocess (`landlock_integration_support.py`).                 |

After Landlock or Popen-facing edits:

```bash
uv run pytest tests/backend/test_landlock_sandbox.py tests/backend/test_landlock_integration_surfaces.py tests/backend/test_sqlite_landlock_temp_store.py -q
```

Skill: `.agents/skills/landlock-sqlite/SKILL.md`.
Host sandbox examples: `docs/en/platform-guides/linux-sandbox.md`.

## Security

| Control      | Note                                                                    |
| ------------ | ----------------------------------------------------------------------- |
| HTTPS/WSS    | On by default (per-identity self-signed when custom PEMs absent)        |
| Auth         | Optional (`--auth` / `MESHCHAT_AUTH=true`)                              |
| CSRF         | Required on mutating HTTP                                               |
| Cookies      | Encrypted session                                                       |
| Middleware   | CORS, CSP, lockout when auth on, optional IP allowlist                  |
| Privacy mode | Blocks outbound clearnet HTTP. Does not stop Reticulum mesh.            |
| Bind         | Prefer `127.0.0.1`. Do not expose to public internet without hardening. |

Sensitive config (auth enable / password hash): CSRF-protected HTTP only, not open WS mutators.
Local FS APIs: path-jail. See `.agents/conventions/path-jail.md`.
Shell URL checks: parse origins, never prefix-match `http://127.0.0.1`. Skill: `url-origin-allowlists`.
Password reset: `--reset-password` or `MESHCHAT_RESET_PASSWORD=true`.

### Plugins

Treat install/enable as security-sensitive.

- Frontend Workers with capability grants
- Backend WASM: wasmtime fuel / capability gates
- Python / Sideband: higher risk, permission-gated
- Invalid RSG signature: hard-block install
- Tampered tree: disable as integrity failure
- Kill switch: `--disable-plugins` / `MESHCHAT_DISABLE_PLUGINS=true`

Skill: `.agents/skills/plugin-install-security/SKILL.md`.

## HTTP and WebSocket

- REST: `/api/v1/*` via `window.api` / `apiClient.js` (CSRF on mutators)
- WS: `/ws` for live events
- Typed WS: frontend `wsEventRegistry` / `wsEventBridge`
- RNS Link API over WS (`rns.link.*`). Docs: `docs/en/rns-link-api.md`
- Startup/DB not ready: prefer **503** retryable over opaque **500**

Frontend/Android surface rules: `.agents/conventions/frontend.md`, `.agents/conventions/android.md`.

## Environment and flags

CLI flags usually mirror these.

| Variable / flag                                            | Purpose                                      |
| ---------------------------------------------------------- | -------------------------------------------- |
| `MESHCHAT_HOST` / `--host`                                 | Bind (default `127.0.0.1`)                   |
| `MESHCHAT_PORT` / `--port`                                 | Port (default `8000`)                        |
| `MESHCHAT_HEADLESS` / `--headless`                         | No auto browser                              |
| `MESHCHAT_STORAGE_DIR` / `--storage-dir`                   | App storage root                             |
| `MESHCHAT_RETICULUM_CONFIG_DIR` / `--reticulum-config-dir` | Reticulum config                             |
| `MESHCHAT_DATA_DIR` / `--data-dir`                         | Portable root when storage + Reticulum unset |
| `MESHCHAT_PUBLIC_DIR` / `--public-dir`                     | Frontend assets                              |
| `MESHCHAT_AUTH` / `--auth`                                 | Enable web auth                              |
| `MESHCHAT_NO_HTTPS` / `--no-https`                         | HTTP instead of HTTPS                        |
| `MESHCHAT_SSL_CERT` + `MESHCHAT_SSL_KEY`                   | Custom TLS PEMs (both required)              |
| `MESHCHAT_IDENTITY_FILE` / `BASE32` / `BASE64`             | Seed identity                                |
| `MESHCHAT_AUTO_RECOVER` / `--auto-recover`                 | DB recovery on startup                       |
| `MESHCHAT_EMERGENCY` / `--emergency`                       | Limited operation                            |
| `MESHCHAT_RESET_PASSWORD` / `--reset-password`             | Clear password hash                          |
| `MESHCHAT_DISABLE_PLUGINS` / `--disable-plugins`           | Disable plugins                              |
| `MESHCHAT_LANDLOCK`                                        | `1` / `0` / unset auto                       |
| `MESHCHAT_SELF_CHECK` / `--self-check`                     | Diagnostics then exit                        |
| `MESHCHAT_MEMORY_DIAG` / `--memory-diag`                   | tracemalloc                                  |
| `MESHCHAT_DISABLE_CSRF`                                    | Dangerous. Tests/dev only                    |
| `MESHCHAT_SKIP_STORAGE_LOCK`                               | Dangerous. Overlapping instances             |
| `MESHCHAT_RNS_LOG_LEVEL`                                   | RNS verbosity                                |
| `MESHCHAT_RNS_LOG_DEST`                                    | `stdout` or rotating logger                  |
| `MESHCHAT_DEBUGPY`                                         | `task debug` listen                          |
| `MESHCHAT_DEBUGPY_PORT`                                    | default 5678 on 127.0.0.1                    |
| `MESHCHAT_DEBUGPY_WAIT`                                    | `1` wait for attach                          |
| `MESHCHAT_VUE_DEVTOOLS`                                    | `0` disables Vite overlay                    |

```bash
meshchatx --restore-db /path/to/backup.zip
```

## Testing

| Change             | Update                                       |
| ------------------ | -------------------------------------------- |
| Backend            | `tests/backend/`                             |
| Frontend           | `tests/frontend/`                            |
| Routes / WS shapes | contract fixtures (see conventions/tests.md) |

Prefer focused suites. Full `task test` is heavy.
Do not pipe long pytest through `| tail` in agent shells.
Landlock-apply tests: subprocess only.
Soak / some notification suites can hang: timeouts, isolate unless requested.
Do not weaken self-check or CI boot probes without cause.
Details: `.agents/conventions/tests.md`, `.agents/skills/test-loop/SKILL.md`.

## License and contributions

Prefer existing SPDX. Project-owned files are `0BSD`. Preserve third-party MIT
headers on able, usb4a, rnode-flasher, and similar embeds.
Flow: `CONTRIBUTING.md`. Generative AI: disclose and human-review. No unreviewed bulk churn.

## High-risk checklist

| Area                          | Verify                                                                                                       |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Identity import / tutorial    | Key-only vs zip copy, picker accepts real exports, activate/skip does not orphan                             |
| Conversations / notifications | Slim queries, MEMORY temp under Landlock, 503 on retryable SQLite, sidebar unread pills sync, no header bell |
| Auth / CSRF / WS              | No new unauthenticated mutators, no sensitive settings over open WS                                          |
| Plugins                       | Permissions declared, consent preserved, signatures not bypassed                                             |
| Android bridges               | MIME map, storage paths, WebView nav guards                                                                  |
| Identity switch               | No cross-identity leakage via caches, routers, globals                                                       |
| Migrations                    | Schema version bump and upgrade path tested                                                                  |

## Product docs

```
docs/en/architecture.md
docs/en/identity-and-security.md
docs/en/getting-started.md
docs/en/rns-link-api.md
docs/en/platform-guides/linux-sandbox.md
docs/en/messaging.md
CHANGELOG.md
CONTRIBUTING.md
```
