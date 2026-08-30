# Nomad Network and Mesh Server

Nomad Network is a distributed page and file system on top of Reticulum. MeshChatX includes a browser for remote nodes and a **Mesh Server** tool for hosting your own pages.

## Nomad browser

Open **Nomad Network** and enter a node destination hash. MeshChatX fetches the default entry page (usually `/page/index.mu`) over Reticulum link requests.

Supported page types:

| Extension | Format                               |
| --------- | ------------------------------------ |
| `.mu`     | Micron markup (NomadNet default)     |
| `.md`     | Markdown with GFM-oriented rendering |
| `.txt`    | Plain text with preserved whitespace |
| `.html`   | Static HTML with sanitised CSS       |

Follow links inside pages to browse further paths on the same node. Download files offered at `/file/*` paths.

Rendering uses `NomadPageRenderer.js` with DOMPurify sanitization. Micron can use a JavaScript parser or optional Go WASM when `nomad_micron_wasm_enabled` is set.

## Favourites and caching

Save frequent nodes as favourites. Link caching (`nomadnet_cached_links`) speeds up repeat visits on slow links.

## Archives

When **page archiver** is enabled, MeshChatX stores versioned snapshots of pages you visit. Open **Archives** to browse historical copies. An optional crawler can archive automatically.

Archived pages use the same renderer as the live browser based on the stored `page_path` extension.

**Private tabs** (incognito icon, purple strip) browse without writing archives, without favourites or Identify, and without reusing the shared Nomad link cache. Private tabs are not restored from localStorage. The destination hash stays out of the URL bar and browser history (same idea as SearXNG keeping queries off GET URLs). They use the same Reticulum process as the active identity. They do not create a separate IdentityContext.

## Mesh Server (page nodes)

**Tools → Mesh Server** lets you run a `nomadnetwork.node` destination locally.

Typical workflow:

1. Create a page node in the UI.
2. Upload `.mu`, `.md`, `.txt`, or `.html` pages and optional files.
3. Start the node and announce it on the mesh.
4. Share your destination hash so others can open `/page/index.mu` on your node.

### Executable (dynamic) pages

You can opt in per node to **executable pages**. When enabled:

- Non-executable pages are served as static files.
- Pages marked executable in the Mesh Server editor run as scripts. On Linux and macOS, `chmod +x` on the page file also marks it.
- The first line must be a shebang such as `#!/usr/bin/env python3`. Windows does not exec scripts by shebang, so Mesh Server resolves that interpreter on PATH (`python`, `py`, `node`, and similar).
- Request `field_*` and `var_*` values are passed as environment variables.
- `link_id` and `remote_identity` are supplied when available.
- Script stdout is returned as the page body. Failures return a controlled error page.

Editing a page in Mesh Server always shows the file source, never the script output.

API endpoints under `/api/v1/page-nodes/` manage CRUD operations, start and stop, and file listings.

Pages are served at `/page/<name>` and files at `/file/<name>` on the node destination.

## Browsing flow

```
User enters destination hash
    |
    v
RNS link request to /page/index.mu (or chosen path)
    |
    v
Remote page node responds with content
    |
    v
NomadPageRenderer picks Micron, Markdown, text, or HTML pipeline
    |
    v
Sanitised HTML shown in Nomad Network view
```

## Authoring pages

Read **NomadNet page formats** for security rules, Markdown quirks, and API behaviour. The Mesh Server rejects disallowed extensions on upload.

## Micron editor

**Tools → Micron editor** helps author `.mu` pages before you upload them to your node.

## See also

- **NomadNet page formats** for detailed authoring reference
- **Tools and utilities** for the full tools list
- **Reticulum interfaces** if remote pages time out (likely a path issue)
