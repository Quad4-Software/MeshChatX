# Tools and utilities

The **Tools** page groups mesh diagnostics and helper apps. Each tool opens its own view with a back link to the grid.

## Network diagnostics

| Tool               | Purpose                                            |
| ------------------ | -------------------------------------------------- |
| Ping               | Measure round-trip time to a reachable destination |
| RNProbe            | Probe whether a destination answers                |
| RNPath             | Inspect the path table                             |
| RNPath-trace       | Trace hops toward a destination                    |
| RNStatus           | Read node status information                       |
| Network visualiser | Graph view of topology (also in main navigation)   |

Use these when messages or pages fail despite interfaces showing as enabled.

## File transfer and shell

| Tool | Purpose                                    |
| ---- | ------------------------------------------ |
| RNCP | Send or fetch files over Reticulum         |
| RNSH | Remote shell sessions with streamed output |

RNCP progress events arrive on the WebSocket as `rncp.transfer.progress`.

## Messaging helpers

| Tool              | Purpose                                         |
| ----------------- | ----------------------------------------------- |
| Propagation nodes | Manage LXMF propagation nodes and sync          |
| Forwarder         | Configure LXMF forwarding rules between aliases |
| Sieve filters     | Pattern-based inbound message filtering (beta)  |
| Message blocklist | Block known unwanted content (beta)             |
| Paper message     | Create or ingest LXMF URIs and QR workflows     |
| Bots              | Run subprocess LXMF bots from templates         |

Bot templates include echo, note, and reminder starters. They use the bundled `lxmfy` package.

## Content and publishing

| Tool          | Purpose                               |
| ------------- | ------------------------------------- |
| Mesh Server   | Host NomadNet-compatible page nodes   |
| Micron editor | Edit `.mu` pages locally              |
| Documentation | MeshChatX guides and Reticulum manual |

## Configuration editors

| Tool                    | Purpose                                 |
| ----------------------- | --------------------------------------- |
| Reticulum config editor | Edit raw Reticulum configuration        |
| Repository server       | Host Python wheels for offline installs |

## Hardware and translation

| Tool          | Purpose                                              |
| ------------- | ---------------------------------------------------- |
| RNode flasher | Flash or update RNode firmware                       |
| Translator    | Translate text via Argos Translate or LibreTranslate |

Translator calls respect **privacy mode**. When privacy mode blocks outbound HTTP, external translation endpoints are not contacted.

## Debugging

| Tool       | Purpose                       |
| ---------- | ----------------------------- |
| Debug logs | View backend debug log stream |

## Coming soon

The registry marks **RNS Tunnel** and **RNS FileSync** as coming soon. They do not have routes in the current release.

## Relay chat server

When `rrc_enabled` is on, you can run a local RRC hub from relay chat server settings. Hubs announce aspect `rrc.hub`. Client UI lives under **Relay chat** in the main navigation.

## Plugins

Installed plugins can add rows to **Tools** and **Navigation** through contribution manifests. Example bundled plugin: **Bug Reports** (`com.meshchatx.mcx-bugs`) for sending redacted debug logs to an `mcx-bugs-v1` collector (or running a collector yourself).

Plugins are capability-gated, not fully open-ended: they cannot rewrite core MeshChatX. Supported packaged runtimes are **frontend JS** (Worker), optional **backend WASM** (wasmtime), and optional **backend Python** (`backend.type: "python"`). Install sources include ZIP archives and single-file **WASM bundles** with embedded `plugin.json` / files / optional RSG signature.

ZIP and WASM installs show a confirmation dialog with requested permissions, scanned/declared external HTTP URLs, signature status (unsigned / signed / trusted / invalid), and heuristic security findings. Invalid signatures hard-block install. You can deny individual grants and optionally trust a valid signer. After install, MeshChatX stores an integrity hash and auto-disables tampered plugins.

Optional **Sideband-compatible** plugins load flat `*.py` files from a configured directory when the master switch is enabled (danger confirm). They run in-process with full host access. Optional sibling `filename.py.rsg` signatures are verified over file bytes.

Sign packages with `scripts/sign-plugin.py` (`sign|verify` for `-dir|-zip|-wasm|-py`) using a Reticulum identity (`rnid` or in-process `RNS.Identity`). MeshChatX plugin signing uses signature file `meshchatx.plugin.rsg` and WASM custom sections `meshchatx.plugin` / `meshchatx.files` / `meshchatx.signature`.

Disable packaged plugins at startup with `--disable-plugins` if you need a minimal surface.

## Command palette

Press the command palette shortcut (configured in settings) to jump to tools and pages without returning to the grid.

## Choosing a tool

```
Symptom                          Tool to try first
-------------------------------- -----------------
No peers visible                 Interfaces, then RNPath
Message stuck sending            RNPath, Propagation nodes
Cannot reach Nomad page          Ping, RNProbe
Need to push a file              RNCP
Remote administration            RNSH (with care)
Want offline Python packages     Repository server
```

## See also

- **Reticulum interfaces** for transport setup
- **LXMF messaging** and **Nomad Network** for feature-specific workflows
- [Plugins](plugins.md) for extending MeshChatX functionality
- **Documentation** for offline manuals
