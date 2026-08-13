---
name: reticulum-interfaces
description: Reticulum interfaces as clothing. Use when editing interface config, RNode/TCP/AutoInterface, interface modes, location_cmd, or any feature that special-cases WiFi vs LoRa vs TCP in application code.
---

# Skill: reticulum-interfaces

Application code talks to destinations and aspects. Interfaces are how this node touches the physical or overlay medium. Do not put WiFi vs LoRa vs TCP branches in message send, call setup, or announce handlers.

Config lives with Reticulum (`~/.reticulum` by default), not only in the identity SQLite database. MeshChatX edits that config through the interface editor and HTTP routes.

## When to use

- Interfaces page, add-interface forms, stats, or discovery
- RNode serial/TCP/BLE, AutoInterface, TCPClient/TCPServer, I2P, or similar
- `location_cmd` or other subprocess fields in interface config
- A feature that wants to "detect LoRa and send smaller packets in the manager"

Packet size and delay belong in protocol design (stamps, attachments, RNCP, PTT), not in `if interface_type == "RNode"`.

## MeshChatX editor rules

`meshchatx/src/backend/interface_editor.py`:

- Allowed modes: `full`, `gateway` (`gw`), `access_point` (`ap` / `accesspoint`), `pointtopoint` (`ptp`), `roaming`, `boundary`, `internal`. Prefer the long form when writing config.
- RNode `tcp://host:port` must store `tcp://<host>` only. Reticulum's TCPConnection calls `socket.getaddrinfo(target_host, 7633)`. An embedded `:port` breaks resolution.
- `location_cmd` is executed by RNS Discovery via `subprocess.run([path])`. Reject shell metacharacters and relative traversal before persisting (`_LOCATION_CMD_FORBIDDEN`).
- Under Landlock, `location_cmd` binaries outside allowed read roots fail with `Permission denied`. Widen `landlock_sandbox.py` on purpose or document `MESHCHAT_LANDLOCK=0` for debugging. See `landlock-sqlite`.

## HTTP and UI

- Routes: `meshchatx/src/backend/http/routes/interfaces.py`
- Serial listing: `meshchatx/src/backend/serial_comports.py` (`GET /api/v1/comports`). Landlock must allow `/sys` or pyserial raises TypeError on USB `idVendor`.
- UI: `meshchatx/src/frontend/components/interfaces/`
- Ownership: `.agents/module-ownership.md` (Interfaces row)

Do not add a WebSocket mutator that writes interface config. CSRF-protected HTTP via `window.api`.

## Tests

Interface stats and editor tests under `tests/backend/` (names in the ownership table). After RNode TCP or `location_cmd` changes, add a focused case next to the existing editor tests.

## Related

- `reticulum-stack` for destination/aspect addressing
- `reticulum-design-gates` before shipping medium-specific behaviour
- `android-webview-bridge` for RNode USB/BLE on Android (jnius shim, usb4a, Able BLE, native flasher)
