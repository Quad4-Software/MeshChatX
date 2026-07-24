# Windows AppContainer sandbox (Landlock equivalent)

MeshChatX on **Windows 10 and Windows 11** can run the backend inside a **Less Privileged AppContainer (LPAC)**. This is the Windows counterpart to Linux **Landlock**: the process loses ambient write access to the user profile and only keeps write access under explicitly granted directories.

Unlike Landlock, Windows cannot lock down an already-running process the same way. Electron therefore starts the frozen backend through a small launcher module that:

1. Creates or reuses the `MeshChatX.Backend` AppContainer profile
2. Grants the package SID read/write ACLs on storage, Reticulum config, logs, temp, and app-owned exchange folders
3. Grants read/execute on the packaged backend tree (needed under LPAC)
4. Starts `ReticulumMeshChatX.exe` inside the container with network capabilities for Reticulum
5. Waits for exit and revokes those ACL grants

## What is allowed

**Writable**

- MeshChatX storage (`--storage-dir` / `%USERPROFILE%\.reticulum-meshchatx` or portable sibling)
- Reticulum config (`--reticulum-config-dir`)
- Log directory (`MESHCHAT_LOG_DIR`, usually `storage/logs`)
- Process temp (`%TEMP%` / `%TMP%`)
- App-owned exchange folders (created if missing):
  - `Documents\MeshChatX`
  - `Downloads\MeshChatX`
  - `Pictures\MeshChatX`

These exchange folders are for attachments and exports. The sandbox does **not** grant access to all of Documents, Downloads, or Pictures.

Electron sets the default download path to `Downloads\MeshChatX` so UI saves land in the same exchange dir the backend can use.

**Readable (execute tree)**

- Packaged backend directory next to `ReticulumMeshChatX.exe`

**Network**

- Internet and private-network AppContainer capabilities are granted so RNS TCP/UDP interfaces keep working. There is no per-host or per-port firewall in this layer.

**Not writable**

- Desktop, and the rest of Documents / Downloads / Pictures outside the `MeshChatX` subfolders
- Arbitrary profile paths and drive roots

Attaching a file from elsewhere still works through the Electron/renderer file picker (bytes uploaded over local HTTPS). The backend does not need to open the original Documents path for that flow.

## Environment override

| Env | Effect |
| --- | --- |
| unset | Auto-enable on Windows when AppContainer APIs are available (Electron desktop default on) |
| `MESHCHAT_APPCONTAINER=0` | Disable (direct backend spawn, no launcher) |
| `MESHCHAT_APPCONTAINER=1` | Force AppContainer. Launch fails hard if APIs or CreateProcess fail |

The sandboxed child sets `MESHCHAT_APPCONTAINER_CHILD=1`. Settings → Network exposure shows AppContainer status next to Landlock/Seccomp.

## Portable installs

When `PORTABLE_EXECUTABLE_DIR` is set, storage and Reticulum dirs live beside the portable exe. The launcher grants ACLs on those portable paths, not only under `%USERPROFILE%`. Exchange folders still use the current user's Documents/Downloads/Pictures Known Folders (including OneDrive redirects when available).

## SQLite

Under AppContainer (same as Landlock), MeshChatX keeps `PRAGMA temp_store=MEMORY` during memory pressure so spill files are not required outside the jail.

## Disable / troubleshoot

- Set `MESHCHAT_APPCONTAINER=0` and restart if a DLL fails to load under LPAC.
- If forced mode fails, check logs for CreateProcess or ACL errors.
- Storage directory changes require a backend restart so ACL grants match the new roots.
- Orphan cleanup uses `taskkill /T` on the launcher PID so the AppContainer child is included.

## Relation to other layers

- Electron renderer still uses Chromium sandbox / fuses.
- Plugin RSG and path jail remain in force inside the container.
- Linux Landlock and Seccomp are unchanged and unused on Windows.

## Manual smoke checklist (Win10 / Win11)

1. Packaged app starts and `/api/v1/status` reports `appcontainer_active: true`
2. Local HTTPS UI on port 9337 loads
3. Messages and RNS interfaces still work
4. Writing a probe file under storage succeeds
5. Writing under `Documents\MeshChatX` succeeds
6. Writing under Desktop or bare Documents from a debug hook fails
7. Quitting Electron stops launcher and child
