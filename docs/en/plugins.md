# Plugins

Plugins extend MeshChatX with extra tools, nav items, and background behaviour. They are capability-gated: a plugin only gets what you grant at install time.

Manage them from **Settings -> Plugins**. Disable every packaged plugin at startup:

```bash
meshchatx --disable-plugins
# or
MESHCHAT_DISABLE_PLUGINS=true
```

## What plugins can do

- Add a row on the **Tools** page
- Add an item in the main **Navigation** sidebar
- React to mesh events (announces, RNS link traffic, LXMF messages, telemetry, file transfers, shell sessions, RRC chat)
- Read conversations, contacts, node announces, telemetry, and app status through bounded managers
- Send text LXMF messages (message.send)
- Keep a private key-value store (storage: isolated)
- Fetch external HTTP resources through the host (network: fetch)
- Read or write the system clipboard (clipboard: read / write)
- Navigate the app to built-in pages
- Draw GeoJSON layers on the map, move the camera, and react to map clicks (map permission)
- Optionally request clearnet HTTP (network: fetch), still subject to **Privacy mode**

WASM backends run in a metered runtime. Python backends run inside MeshChatX and can access files, processes, and network available to the app user. Grant `backend:python` only to code you trust. Sideband Python plugins are separate flat-file plugins with their own danger switch.

## Runtimes

| Runtime        | Where it runs             | Trust level                                       |
| -------------- | ------------------------- | ------------------------------------------------- |
| Frontend JS    | Browser Web Worker        | Medium. Sandboxed worker, capability grants       |
| Backend WASM   | wasmtime on the server    | Medium. Fuel-metered, capability-gated host       |
| Backend Python | In-process with MeshChatX | Full app-user privileges, explicit grant required |
| Sideband *.py  | In-process, flat files    | Highest. Opt-in danger switch, full host access   |

A packaged plugin can ship frontend only, backend only, or both.

## Install flow

```
Pick ZIP or .wasm file in Settings -> Plugins
    |
    --> Preview (permissions, URLs, signature, findings)
    |
    --> You grant or deny each capability
    |
    --> Optional: trust a valid signer
    |
    --> Install + integrity hash stored
    |
    --> Enable
    |
    --> Frontend Worker loads (if present)
    --> Backend WASM / Python activates (if present)
```

Invalid signatures hard-block install. Unsigned packages are allowed. Present-but-broken signatures are not.

After install, MeshChatX hashes the on-disk tree. If files change outside the app, the plugin is auto-disabled as tampered.

## Bundled example: Hello Example

com.meshchatx.mcx-hello ships with MeshChatX. It is a minimal reference plugin: it activates a Python backend, keeps a counter in isolated plugin storage, and renders a small page through api.setUi. Its bundled manifest declares `backend:python`. Enabling it runs that code in-process. It requests no manager permissions or network access.

## Plugin UI (uiDescriptor v1)

Frontend plugins push a JSON tree through api.setUi(descriptor). The host renders it with PluginSlotNode. Allowed types include text, input, number, select, checkbox, button, badge, actions, section, list, row, column, tabs, table, code, empty, progress, separator, image (plugin asset URLs only), widget (manifest ui.widgets allowlist), and html-frame (requires permissions.ui: sandboxed-html).

Styling uses host semantic theme tokens. Plugins choose variants such as primary, secondary, danger, or text variants. They cannot pass arbitrary CSS classes.

Worker helpers: api.callManager(capability, args), api.clipboardWrite(text), api.getTheme(), api.hasPermission(permissionId), api.onThemeChange(handler). `api.hasPermission` is true only for a permission declared by the manifest and granted at install time. `api.clipboardWrite` requires the `clipboard: write` permission. Direct network connections from frontend workers are blocked. Use a Python backend for approved network access.

Layout:

```
mcx-hello/
    plugin.json
    frontend/main.js
    backend/main.py
    locales/en.json
```

Use it as the reference package when building your own.

## Manifest (plugin.json)

Every packaged plugin needs a root plugin.json.

```json
{
    "id": "com.example.my-plugin",
    "version": "1.0.0",
    "apiVersion": 1,
    "name": "My Plugin",
    "description": "Adds a custom tool.",
    "frontend": {
        "entry": "frontend/main.js",
        "type": "js"
    },
    "backend": {
        "entry": "backend/main.py",
        "type": "python"
    },
    "i18n": {
        "directory": "locales",
        "defaultLocale": "en"
    },
    "contributes": {
        "navItems": [
            {
                "id": "my-plugin",
                "route": { "name": "plugin-my-plugin" },
                "icon": "puzzle",
                "labelKey": "nav"
            }
        ],
        "toolsPageEntries": [
            {
                "name": "my-plugin",
                "route": { "name": "plugin-my-plugin" },
                "icon": "puzzle",
                "titleKey": "title",
                "descriptionKey": "description"
            }
        ]
    },
    "permissions": {
        "hooks": ["announce.received"],
        "managers": ["destinationPath.read"],
        "storage": "isolated",
        "network": "none"
    }
}
```

Notes:

- id is reverse-DNS style and must stay stable across versions
- apiVersion is currently 1
- Plugin strings live in the plugin bundle (locales/{locale}.json), not core en.json
- contributes wires UI slots through the frontend registries

## Permissions

Nothing is available unless it is declared in the manifest and granted in the install dialog.

### Hooks

| Hook                      | When it fires                                                        |
| ------------------------- | -------------------------------------------------------------------- |
| announce.received         | A Reticulum announce arrives                                         |
| rns.link.event            | Generic RNS Link traffic (packet_received, link_closed)              |
| lxmf.message.created      | A new LXMF message is stored                                         |
| lxmf.message.deleted      | An LXMF message is deleted                                           |
| lxmf.message.state        | An LXMF message state changes (sent, delivered, failed, ...)         |
| lxmf.delivery             | An LXMF delivery attempt completes                                   |
| lxmf.telemetry            | Peer telemetry arrives                                               |
| file.transfer.progress    | An RNCP file transfer reports progress                               |
| file.download.started     | A NomadNet file download starts                                      |
| file.download.cancelled   | A NomadNet file download is cancelled                                |
| shell.session             | An RNSH or RNX shell session changes state                           |
| shell.output              | An RNSH or RNX shell produces output (may contain sensitive terminal data) |
| rrc.message               | An RRC chat message arrives                                          |

`announce.received` and `rns.link.event` are delivered by the backend as WebSocket `plugin.event` frames. The LXMF, file, shell, and RRC hooks are delivered by the frontend PluginHost, which subscribes to the matching internal WebSocket events only for plugins granted the hook. Payloads over 64 KiB are dropped. Hook events reach the plugin Worker through `api.onEvent(name, handler)`.

### Managers

| Manager              | Purpose                                              |
| -------------------- | ---------------------------------------------------- |
| destinationPath.read | Read the Reticulum path table                        |
| debugLog.read        | Read redacted debug logs                             |
| status.read          | Read app version, privacy mode flag, and row counts  |
| contacts.read        | List contacts (name, hashes, addresses)              |
| nodes.read           | List known node announces                            |
| conversations.list   | List LXMF conversations                              |
| messages.read        | Read messages in one conversation                    |
| message.send         | Send a text LXMF message                             |
| telemetry.read       | Read latest or historical peer telemetry             |
| rnsLink.open         | Open or reuse an RNS link                            |
| rnsLink.identify     | Identify on a cached link                            |
| rnsLink.request      | Request/response on a link                           |
| rnsLink.send         | Send a raw link packet                               |
| rnsLink.close        | Tear down a cached link                              |

Call managers from a plugin with POST /api/v1/plugins/{id}/invoke and method: "callManager", or `api.callManager(capability, args)` in a frontend Worker. Details for the link transport are in [RNS Link API](rns-link-api.md).

Read managers return bounded, sanitized rows: `contacts.read` allows at most 500 rows per call, `nodes.read` 500, `conversations.list` 500, `messages.read` 200, and `telemetry.read` 500. Conversation rows carry metadata only (peer hash, state, timestamps, attachment flags, and the latest message title); message bodies are never included, so reading content requires `messages.read`. Telemetry rows are unpacked into the same shape the telemetry API returns. `message.send` accepts `destination_hash` (64 hex chars), `content` (max 128 KiB), optional `title` (max 500 chars) and `reply_to_hash`. It sends text only: no attachments, telemetry, commands, or reactions. Sending is refused while demo mode is active.

### Storage and network

| Permission        | Effect                                                                |
| ----------------- | --------------------------------------------------------------------- |
| storage: isolated | Private key-value store in the MeshChatX database                     |
| storage: none     | No plugin storage                                                     |
| network: fetch    | Lets the plugin make outbound HTTP requests through the host          |
| network: none     | No clearnet fetch                                                     |
| clipboard: read   | Lets the plugin read the system clipboard                             |
| clipboard: write  | Lets the plugin write text to the system clipboard                    |
| clipboard: read-write | Both clipboard directions (grants `clipboard:read` and `clipboard:write`) |
| map: read         | Read map view state and subscribe to map click and move events        |
| map: write        | Add and update plugin map layers and move the map camera              |
| backend: python   | Runs Python code in-process with the app user's full local privileges |

Map access is declared as `"map": "none" | "read" | "write" | "read-write"` in `permissions`. `read-write` grants both `map:read` and `map:write`. Clipboard access is declared the same way with `"clipboard": "none" | "read" | "write" | "read-write"`.

Install preview also scans plugin files for external http:// / https:// URLs and shows them before you grant network access.
`network: fetch` is not a sandbox for Python code. Once `backend:python` is granted, Python code can use the process's network access directly.

Frontend fetch goes through POST /api/v1/plugins/{id}/fetch, which enforces the `network:fetch` grant, refuses requests while privacy mode is on, and only allows http(s) URLs without embedded credentials or non-public IP literals. Before each request (including every redirect hop, up to 3) the backend resolves the hostname and requires all answers to be globally routable addresses, so DNS names pointing at loopback or LAN space are rejected. Methods are limited to GET, HEAD, POST, PUT, PATCH, DELETE, and OPTIONS; bodies are capped at 256 KiB and responses at 1 MiB (flagged `truncated` when cut). The whole exchange including DNS and redirects is capped at 30 seconds. Host, Content-Length, Transfer-Encoding, and hop-by-hop headers are dropped from requests, Set-Cookie response headers are never returned, and Authorization/Cookie headers are stripped when a redirect crosses origins. The result includes the final `url` after redirects. DNS answers are validated at request time but not pinned to the connection, so a domain whose DNS changes between lookup and connect (rebinding) is not fully defended; grant `network: fetch` only to plugins you trust.

## How a frontend plugin runs

```
Settings enable plugin
    |
    --> PluginHost loads /api/v1/plugins
    |
    --> Fetch frontend entry as text
    |
    --> Spawn pluginWorker.js (module Worker)
    |
    --> Register nav / tools contributions
    |
    --> Subscribe to plugin.event on /ws (if hooks granted)
    |
    --> Worker may invoke backend via /api/v1/plugins/{id}/invoke
```

The Worker talks to the host with typed messages (init, event, request). The host never gives the Worker a raw privileged API.

## Map API

Frontend plugins with the map permission get `api.map`. The bundled `com.meshchatx.mcx-map-demo` plugin is a working reference.

```js
const { layerId } = await api.map.addLayer({ id: "zones", name: "Zones" });
await api.map.setLayerData(layerId, {
    type: "FeatureCollection",
    features: [
        {
            type: "Feature",
            geometry: { type: "Point", coordinates: [16.37, 48.2] },
            properties: { name: "Checkpoint", "marker-color": "#dc2626" },
        },
    ],
});
await api.map.setView({ center: [16.37, 48.2], zoom: 14, navigate: true });
```

Layers take a GeoJSON FeatureCollection (a single Feature is accepted too). Feature properties style the render: `marker-color` and `marker-size` for points, `stroke`, `stroke-width`, `fill`, and `fill-opacity` for lines and polygons, same convention as imported overlays. Limits: 2 MB of GeoJSON and 20,000 features per update, 64 layers per plugin.

| Method                              | Permission | Returns                                                      |
| ----------------------------------- | ---------- | ------------------------------------------------------------ |
| `api.map.isAvailable()`             | none       | `{ available, active }`                                      |
| `api.map.getState()`                | map:read   | `{ available, active, center, zoom, bearing, bounds, size }` |
| `api.map.setView(view)`             | map:write  | updated state                                                |
| `api.map.addLayer(opts)`            | map:write  | `{ layerId }`                                                |
| `api.map.setLayerData(id, geojson)` | map:write  | `{ layerId, featureCount }`                                  |
| `api.map.removeLayer(id)`           | map:write  | `{ layerId, removed }`                                       |
| `api.map.clearLayers()`             | map:write  | `{ cleared }`                                                |

`setView` accepts `center` as `[lon, lat]`, `zoom` 0-22, `bearing` in degrees, `durationMs`, and `navigate`. It resolves after the camera animation finishes and returns the resulting state. Pass `navigate: true` to open the Map page first when no map is active; without it the call fails with `map_not_open`. Layer writes never navigate, they apply silently to every open map and are replayed when a map is created later. All plugin layers are removed when the plugin unloads.

Map events use `api.map.on(event, handler)`, which returns a subscription id for `api.map.off(id)`:

| Event          | Payload                                        |
| -------------- | ---------------------------------------------- |
| `click`        | `{ lat, lon, pixel }`                          |
| `moveend`      | same shape as `getState()`                     |
| `featureclick` | `{ lat, lon, layerId, featureId, properties }` |

`featureclick` fires when a click lands on one of the plugin's own layer features, with the feature's GeoJSON properties.

## Worker APIs

Frontend plugins get a small set of host-mediated APIs on the `api` object. Each one checks the matching granted permission in the Worker and again in the PluginHost or backend, so a plugin cannot use a capability it was not granted.

### Storage

Requires `storage: isolated`. Backed by the same per-plugin key/value store the Python host uses: keys are 1-256 characters, values up to 256 KiB.

```js
await api.storage.set("seen_peers", JSON.stringify([...]))
const raw = await api.storage.get("seen_peers")   // string or null
const keys = await api.storage.keys()            // up to 500 keys
await api.storage.delete("seen_peers")           // true when a key was removed
await api.storage.clear()                        // number of keys removed
```

### Network fetch

Requires `network: fetch`. `api.net.fetch(url, options)` returns `{ status, status_text, headers, body, truncated }`. `options` accepts `method`, `headers` (object, max 32 entries), and `body` (string, max 256 KiB). Requests are refused while privacy mode is enabled and while the URL is not a plain http(s) address. The body is always text; binary responses come back UTF-8 decoded with replacement characters.

### App navigation

`api.app.navigate(route, params)` pushes a named route through the app router. Only built-in route names are allowed (messages, contacts, map, settings, tools, and the other top-level pages); plugin routes, popouts, and arbitrary URLs are rejected. Example: `await api.app.navigate("messages", { destinationHash: peer })`.

### Clipboard

`api.clipboardWrite(text)` needs `clipboard: write`. `api.clipboardRead()` needs `clipboard: read` (or `read-write`) and resolves to the clipboard text. Reads can be denied by the browser or OS, in which case the promise rejects.

### Events

`api.onEvent(name, handler)` receives hook payloads. Backend hooks (`announce.received`, `rns.link.event`) arrive via `plugin.event`; the LXMF, file transfer, shell, and RRC hooks listed in the permissions table arrive via the PluginHost WebSocket bridge. Each subscription is cleaned up automatically when the plugin unloads.

## How a backend plugin runs

```
Enable plugin
    |
    +--> type: wasm  --> load into wasmtime, fuel + host caps
    |
    +--> type: python --> import entry, call activate(host)
    |
    --> Hooks fan out from PluginManager
    |
    --> invoke(method, args) for RPC from the UI Worker
```

Python host surface (permission-checked):

- host.log(message)
- host.call_manager(capability, args)
- host.storage_get(key) / host.storage_set(key, value)
- host.network_fetch_allowed()

## Packaging and signing

Distribute as:

1. **ZIP** with plugin.json and assets
2. **WASM bundle** (single .wasm with embedded manifest / files / optional signature)

Signature file for ZIP/dir packages: meshchatx.plugin.rsg

WASM custom sections:

```
meshchatx.plugin      --> embedded plugin.json
meshchatx.files       --> embedded text assets
meshchatx.signature   --> RSG over payload without this section
```

Canonical ZIP signing uses sorted paths and fixed 1980-01-01 mtimes. The signature file itself is excluded from the signed payload.

Sign and verify with:

```bash
python3 scripts/sign-plugin.py sign-dir ./my-plugin --identity <rnid>
python3 scripts/sign-plugin.py verify-dir ./my-plugin
python3 scripts/sign-plugin.py sign-zip ./my-plugin.zip --identity <rnid>
python3 scripts/sign-plugin.py sign-wasm ./plugin.wasm --identity <rnid>
python3 scripts/sign-plugin.py sign-py ./legacy_plugin.py --identity <rnid>
```

Trust status in the UI:

```
No .rsg present
    --> Unsigned (install allowed)

Valid .rsg, signer unknown
    --> Signed (you can add to Trusted Publishers)

Valid .rsg, signer in Trusted Publishers
    --> Trusted

Broken / mismatched .rsg
    --> Invalid (install blocked)
```

## Sideband-compatible plugins

Legacy Sideband-style flat *.py files are separate from packaged ZIP/WASM plugins.

```
Settings -> Plugins -> Sideband
    |
    --> Confirm danger prompt
    |
    --> Set directory of *.py files
    |
    --> Optional filename.py.rsg next to each script
    |
    --> Reload
```

These run in-process with full host access. They are not ZIP-permission gated. Keep the master switch off unless you trust every file in that directory.

## Operator tips

- Prefer signed packages from publishers you added yourself
- Deny network: fetch unless the plugin needs clearnet HTTP
- Prefer WASM backends over Python when you can
- Use --disable-plugins when diagnosing weird UI or backend behaviour
- Treat Sideband plugins like running arbitrary local scripts

## See also

- [Tools and utilities](tools.md) for the Tools page and contribution overview
- [RNS Link API](rns-link-api.md) for rnsLink.* and rns.link.event
- [Architecture and design](architecture.md) for the plugin runtime overview
- [Identities, privacy, and security](identity-and-security.md) for signing and Privacy mode
