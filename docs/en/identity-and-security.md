# Identities, privacy, and security

MeshChatX separates cryptographic identities, network security, and optional privacy controls. This page summarises how they interact.

## Identities

Each identity is a Reticulum key pair with its own:

- SQLite database and LXMF router directory
- Settings in the config table via ConfigManager
- Storage path under `storage/identities/<identity_hash>/`

Create, import, or switch identities from **Identities**. Only one identity is active in the UI at a time. Switching runs a teardown path so routers and managers do not leak state.

Shared resources include the Reticulum process and interface configuration in ~/.reticulum unless you override paths.

## Announces

MeshChatX tracks announces for aspects such as:

| Aspect            | Meaning                           |
| ----------------- | --------------------------------- |
| lxmf.delivery     | Peer accepts LXMF messages        |
| lxst.telephony    | Peer accepts LXST calls           |
| lxmf.propagation  | Propagation node                  |
| nomadnetwork.node | NomadNet page server              |
| rrc.hub           | Relay chat hub (when RRC enabled) |
| map-data-v1       | Published GeoJSON/KML/KMZ packs   |

Announce records store signal metadata and parsed app data for display names and icons.

## Web UI authentication

Optional HTTP basic authentication is enabled with --auth or MESHCHAT_AUTH=true. Sessions use encrypted cookies. Mutating API requests require CSRF tokens.

Access attempts are logged. Repeated failures can trigger lockout when auth is enabled.

Reset a forgotten password with --reset-password or MESHCHAT_RESET_PASSWORD=true, then set a new password in the UI.

### Demo mode

MESHCHAT_DEMO_MODE=1 (or --demo) enables a public showcase profile: privacy mode on, plugins off, no outbound announces, and a default-deny HTTP mutation policy with mesh send blocked. Status reports demo_mode: true.

MESHCHAT_AUTH_PAGE_HINT sets optional plain text on the login page (independent of demo mode). Demo Docker compose defaults to username and password hints for the showcase account.

MESHCHAT_AUTH_BYPASS=1 skips session auth for local testing only. Do not use it on internet-facing deployments.

## Transport security

- HTTPS and WSS are on by default.
- Self-signed certificates are generated per identity when custom PEM files are missing.
- Pass --ssl-cert and --ssl-key for managed certificates.
- Use --no-https only on trusted loopback setups.
- WebSocket upgrades require a same-authority Origin when the browser sends one. Missing Origin is allowed on loopback binds (and when password auth is enabled) so local non-browser tools keep working. On a non-loopback bind without password auth, a missing Origin is rejected.
- /ws inbound messages are rate-limited per connection. Nomad file downloads over WS are capped (default 10 MiB) and large transfers use chunked frames. Debug counters are at GET /api/v1/debug/websocket.

Electron loads the UI from the local HTTPS origin served by the embedded backend.

## IP allowlisting

app_security_settings can restrict which client IPs may use the web UI. Combine with auth when exposing the service beyond localhost.

## Privacy mode

**Privacy mode** blocks outbound HTTP from MeshChatX features that would otherwise call the public internet. Translation and similar tools respect this flag.

Privacy mode does not disable Reticulum mesh traffic. It limits clearnet fetches from the app itself.

## Linux sandboxing

On Linux, MeshChatX can enable two complementary in-process sandboxes when supported:

- **Landlock** restricts filesystem paths the backend may use. User-local pipx tools (for example Argos Translate under ~/.local) need explicit read and sometimes write roots. See **Linux sandboxing** in Platform guides.
- **Seccomp-BPF** installs a syscall denylist (via libseccomp) that blocks kernel-admin and related calls a mesh client does not need.

Both auto-enable when available and fall back to a no-op when the platform, kernel, or libraries cannot support them. Override with:

```bash
MESHCHAT_LANDLOCK=0   # or 1 to force
MESHCHAT_SECCOMP=0    # or 1 to force
```

Android never enables these in-process sandboxes (the Android app seccomp policy already constrains the process, and Landlock syscalls are blocked there).

See **Linux sandboxing** in Platform guides for optional Firejail and Bubblewrap wrappers around the host install.

## Windows Electron AppContainer

Windows desktop builds can spawn the Python backend inside an LPAC AppContainer when MESHCHAT_APPCONTAINER=1. Default installs start the backend directly without that wrapper. Check /api/v1/server/security for appcontainer_active when debugging sandbox-related SQLite or filesystem errors on Windows.

## Blocking and filtering

Use **Blocked** for specific destination hashes. Combine with sieve filters, message blocklists, and LXMF stamp policies described in **LXMF messaging**.

## Data backup

Database backups land in database-backups/. Before a schema upgrade, MeshChatX writes a backup-pre-migrate-v*-to-v*.zip in that folder unless MESHCHAT_SKIP_PRE_MIGRATE_BACKUP=1. After a successful migration it runs PRAGMA quick_check and keeps the five newest pre-migrate zips (override with MESHCHAT_PRE_MIGRATE_BACKUP_KEEP, 0 disables pruning). If the stored schema version is newer than this build supports, startup refuses to migrate. Only one process should use a given identity storage directory at a time (storage lock). Roll back by restoring a backup zip and running an older MeshChatX build. Export snapshots from **About** or the API. Electron crash recovery can offer restore when integrity checks fail.

CLI examples:

```bash
meshchatx --list-backups
meshchatx --export-backup /path/to/export.zip
meshchatx --export-backup backup-20260101-120000.zip /path/to/copy.zip
meshchatx --restore-db /path/to/backup.zip
```

When the backend can start briefly, or you run from source:

```bash
meshchatx --storage-dir /path/to/storage --restore-db /path/to/backup.zip
```

## Database corruption and data reset

If MeshChatX fails to start with errors such as database disk image is malformed, DatabaseError, or corrupted ratchet data, the desktop crash screen offers:

- Restore latest backup from database-backups/ or snapshots/ inside the MeshChatX storage folder
- Choose backup file for a zip you saved elsewhere
- Try auto-repair (--auto-recover: SQLite checkpoint / integrity pass)
- Emergency mode, which opens the app without the database so you can export from About when possible
- Copy reset instructions with the folders to delete for a clean reinstall

### Storage locations

| Platform         | MeshChatX storage                              | Reticulum network stack              |
| ---------------- | ---------------------------------------------- | ------------------------------------ |
| Linux / macOS    | ~/.reticulum-meshchatx/                        | ~/.reticulum/                        |
| Windows          | `%USERPROFILE%\.reticulum-meshchatx\`          | `%USERPROFILE%\.reticulum\`          |
| Windows portable | `<MeshChatX.exe folder>\.reticulum-meshchatx\` | `<MeshChatX.exe folder>\.reticulum\` |

Legacy Reticulum MeshChat data may still exist at ~/.reticulum-meshchat/ (or the Windows equivalent). Automatic database backups go to database-backups/ inside the MeshChatX storage folder after a successful run.

### Complete removal

Quit MeshChatX. On Windows, also end ReticulumMeshChatX.exe in Task Manager if it is still running. Then delete the MeshChatX storage folder and the Reticulum config folder for your install type. That removes the local identity, messages, contacts, path cache, and ratchet state. The next launch creates a new identity unless you restore a backup first.

Linux / macOS:

```bash
rm -rf ~/.reticulum-meshchatx ~/.reticulum ~/.reticulum-meshchat
```

Windows PowerShell:

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.reticulum-meshchatx", "$env:USERPROFILE\.reticulum", "$env:USERPROFILE\.reticulum-meshchat" -ErrorAction SilentlyContinue
```

If you pass --storage-dir or --reticulum-config-dir, delete those directories instead.

## Integrity checks

Startup integrity verification runs in packaged Electron builds and can be triggered from the backend. Failed checks surface recovery options instead of silently corrupting data.

## Plugin signing and trust

Packaged plugins may include a Reticulum Signature (.rsg) over a canonical ZIP payload (sorted paths, fixed 1980-01-01 mtimes, signature file excluded). MeshChatX plugin signing writes meshchatx.plugin.rsg and WASM sections meshchatx.plugin / meshchatx.files / meshchatx.signature.

Policy:

- Unsigned packages are allowed
- Present but invalid signatures hard-block install
- Valid signers can be added to a user trusted-publishers list (ignored if the list file is tampered outside MeshChatX)
- Installed plugin trees get an integrity hash, on-disk changes disable the plugin as tampered

Sideband Python plugins are opt-in via a master danger switch. They are not ZIP-permission gated. Optional per-file .py.rsg signatures are verified over script bytes.

## Safe deployment patterns

```
Recommended for most users
    |
    v
Bind 127.0.0.1, use HTTPS, enable auth if others use the same host
    |
    v
Add interfaces only for meshes you trust
    |
    v
Keep backups and test restore on upgrades
```

Avoid exposing port 8000 directly to the internet without a reverse proxy, strong auth, and network-level filtering. MeshChatX is designed as a personal or small-team operator console, not a multi-tenant public website.

## Multi-user hosts

On shared computers, use separate OS user accounts or separate --storage-dir values so SQLite databases and identity files do not overlap.

## See also

- **Architecture and design** for session and API details
- **Installation and setup** for CLI security flags
- Reticulum manual cryptography chapters for identity math
