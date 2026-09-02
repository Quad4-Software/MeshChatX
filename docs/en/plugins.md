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
- React to mesh events (announces, RNS link traffic)
- Call narrowly declared backend managers (path table, debug log, bug reports, RNS links)
- Keep a private key-value store (storage: isolated)
- Optionally fetch clearnet HTTP (network: fetch), still subject to **Privacy mode**

Plugins cannot rewrite core MeshChatX. They do not get open-ended filesystem or process control unless you opt into Sideband Python plugins (see below).

## Runtimes

| Runtime        | Where it runs             | Trust level                                     |
| -------------- | ------------------------- | ----------------------------------------------- |
| Frontend JS    | Browser Web Worker        | Medium. Sandboxed worker, capability grants     |
| Backend WASM   | wasmtime on the server    | Medium. Fuel-metered, capability-gated host     |
| Backend Python | In-process with MeshChatX | High. Permission-checked in-process host        |
| Sideband *.py  | In-process, flat files    | Highest. Opt-in danger switch, full host access |

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

## Bundled example: Bug Reports

com.meshchatx.mcx-bugs ships with MeshChatX. It is a local issue tracker with opt-in redacted mesh send on aspect mcx-bugs-v1. Local Issues groups exceptions by fingerprint. Send never runs automatically. Collect runs a mesh collector with inbound redaction and durable storage under the active identity.

## Plugin UI (uiDescriptor v1)

Frontend plugins push a JSON tree through api.setUi(descriptor). The host renders it with PluginSlotNode. Allowed types include text, input, number, select, checkbox, button, badge, actions, section, list, row, column, tabs, table, code, empty, progress, separator, image (plugin asset URLs only), widget (manifest ui.widgets allowlist), and html-frame (requires permissions.ui: sandboxed-html).

Styling uses host semantic theme tokens. Plugins choose variants such as primary, secondary, danger, or text variants. They cannot pass arbitrary CSS classes.

Worker helpers: api.callManager(capability, args), api.clipboardWrite(text), api.getTheme(), api.onThemeChange(handler).

Layout:

```
mcx-bugs/
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

| Hook              | When it fires                                           |
| ----------------- | ------------------------------------------------------- |
| announce.received | A Reticulum announce arrives                            |
| rns.link.event    | Generic RNS Link traffic (packet_received, link_closed) |

Hook events reach the UI as WebSocket plugin.event frames, then into the plugin Worker.

### Managers

| Manager              | Purpose                       |
| -------------------- | ----------------------------- |
| destinationPath.read | Read the Reticulum path table |
| debugLog.read        | Read redacted debug logs      |
| bugReport.*          | Bug report / collector APIs   |
| rnsLink.open         | Open or reuse an RNS link     |
| rnsLink.identify     | Identify on a cached link     |
| rnsLink.request      | Request/response on a link    |
| rnsLink.send         | Send a raw link packet        |
| rnsLink.close        | Tear down a cached link       |

Call managers from a plugin with POST /api/v1/plugins/{id}/invoke and method: "callManager". Details for the link transport are in [RNS Link API](rns-link-api.md).

### Storage and network

| Permission        | Effect                                                                |
| ----------------- | --------------------------------------------------------------------- |
| storage: isolated | Private key-value store in the MeshChatX database                     |
| storage: none     | No plugin storage                                                     |
| network: fetch    | Outbound HTTP allowed (still blocked by Privacy mode when that is on) |
| network: none     | No clearnet fetch                                                     |

Install preview also scans plugin files for external http:// / https:// URLs and shows them before you grant network access.

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
