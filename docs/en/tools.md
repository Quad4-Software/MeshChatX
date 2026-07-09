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

Installed plugins can add rows to **Tools** and **Navigation** through contribution manifests. Example bundled plugin: **Mesh Observatory** (`com.meshchatx.mesh-observatory`) for live announce feeds and path tables.

Plugins are capability-gated, not fully open-ended: they cannot rewrite core MeshChatX. Supported runtimes are **frontend JS** (Worker) and optional **backend WASM**. Python plugins are not supported.

ZIP install shows a confirmation dialog that lists requested permissions (hooks, managers, storage, `network:fetch`) and any scanned/declared external HTTP URLs. You can deny individual grants before install; denied capabilities stay blocked at runtime. Misbehaving plugins auto-disable after an error budget.

Plugins that need a generic Reticulum Link transport (for example a microReticulum node management UI) can request `rnsLink.*` manager capabilities and the `rns.link.event` hook. External web apps can use the same transport over `/ws` without installing a plugin. See **RNS Link API**.

Disable plugins at startup with `--disable-plugins` if you need a minimal surface.

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
- **Documentation** for offline manuals
