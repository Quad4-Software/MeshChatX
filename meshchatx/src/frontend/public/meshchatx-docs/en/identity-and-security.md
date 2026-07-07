# Identities, privacy, and security

MeshChatX separates cryptographic identities, network security, and optional privacy controls. This page summarises how they interact.

## Identities

Each identity is a Reticulum key pair with its own:

- SQLite database and LXMF router directory
- Settings in the `config` table via `ConfigManager`
- Storage path under `storage/identities/<identity_hash>/`

Create, import, or switch identities from **Identities**. Only one identity is active in the UI at a time. Switching runs a teardown path so routers and managers do not leak state.

Shared resources include the Reticulum process and interface configuration in `~/.reticulum` unless you override paths.

## Announces

MeshChatX tracks announces for aspects such as:

| Aspect              | Meaning                           |
| ------------------- | --------------------------------- |
| `lxmf.delivery`     | Peer accepts LXMF messages        |
| `lxst.telephony`    | Peer accepts LXST calls           |
| `lxmf.propagation`  | Propagation node                  |
| `nomadnetwork.node` | NomadNet page server              |
| `rrc.hub`           | Relay chat hub (when RRC enabled) |

Announce records store signal metadata and parsed app data for display names and icons.

## Web UI authentication

Optional HTTP basic authentication is enabled with `--auth` or `MESHCHAT_AUTH=true`. Sessions use encrypted cookies. Mutating API requests require CSRF tokens.

Access attempts are logged. Repeated failures can trigger lockout when auth is enabled.

Reset a forgotten password with `--reset-password` or `MESHCHAT_RESET_PASSWORD=true`, then set a new password in the UI.

## Transport security

- HTTPS and WSS are on by default.
- Self-signed certificates are generated per identity when custom PEM files are missing.
- Pass `--ssl-cert` and `--ssl-key` for managed certificates.
- Use `--no-https` only on trusted loopback setups.

Electron loads the UI from the local HTTPS origin served by the embedded backend.

## IP allowlisting

`app_security_settings` can restrict which client IPs may use the web UI. Combine with auth when exposing the service beyond localhost.

## Privacy mode

**Privacy mode** blocks outbound HTTP from MeshChatX features that would otherwise call the public internet. Translation and similar tools respect this flag.

Privacy mode does not disable Reticulum mesh traffic. It limits clearnet fetches from the app itself.

## Linux sandboxing

Optional Landlock sandboxing on Linux restricts filesystem access for the backend. See **Linux sandboxing** in Platform guides for Firejail and Bubblewrap examples.

## Blocking and filtering

Use **Blocked** for specific destination hashes. Combine with sieve filters, message blocklists, and LXMF stamp policies described in **LXMF messaging**.

## Data backup

Database backups land in `database-backups/`. Export snapshots from **About** or the API. Electron crash recovery can offer restore when integrity checks fail.

CLI restore example:

```bash
meshchatx --restore-db /path/to/backup.zip
```

## Integrity checks

Startup integrity verification runs in packaged Electron builds and can be triggered from the backend. Failed checks surface recovery options instead of silently corrupting data.

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

On shared computers, use separate OS user accounts or separate `--storage-dir` values so SQLite databases and identity files do not overlap.

## See also

- **Architecture and design** for session and API details
- **Installation and setup** for CLI security flags
- Reticulum manual cryptography chapters for identity math
