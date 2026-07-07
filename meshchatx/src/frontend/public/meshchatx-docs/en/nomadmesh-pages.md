# NomadNet page formats

MeshChatX serves pages from a **Mesh Server** page node and displays them in the **Nomad Network** browser. Pages are fetched with the Nomad path convention `/page/<filename>`.

## Supported filenames

| Extension | Role                                                    |
| --------- | ------------------------------------------------------- |
| `.mu`     | Micron markup (NomadNet default)                        |
| `.md`     | Markdown with GitHub-flavored features via the renderer |
| `.txt`    | Plain text with escaped HTML and preserved whitespace   |
| `.html`   | Static HTML with CSS only (see security below)          |

If you add a page without a recognised extension, the server stores it as `.mu`. Filenames with other extensions (for example `.exe`) are rejected when saving through the API.

## Plain text (`.txt`)

Content is HTML-escaped and shown with pre-wrapped whitespace. There is no Markdown parsing on `.txt` pages.

## Markdown (`.md`)

**Not the same engine as chat.** Conversations use the lightweight `MarkdownRenderer` in the messaging UI. Nomad `.md` pages use `marked` with GFM-oriented rules plus sanitisation. Features and edge cases can differ between the two paths. Automated tests cover both.

Authoring tips:

- Use ATX headings with a hash and a space before the title, for example `# Title`, `## Section`, `#### Subsection`.
- Fenced code blocks keep indentation.
- Off-mesh `http` and `https` links in rendered content are removed or restricted so the preview cannot drive external navigation without mesh-style URLs.

## HTML (`.html`)

- **JavaScript** is not executed. `script` tags and event-handler attributes are stripped.
- **External resources** are blocked where possible. `@import` and `url(...)` pointing at `http://`, `https://`, or protocol-relative URLs are removed from CSS.
- Embedded `<style>` blocks are kept. Rules that target `html` or `body` are rewritten to apply to the viewer root container.
- **Links** must be mesh-style (`:` paths, 32-character hex prefixes, `/page/...`, `/file/...`, or `#` fragments) or they are removed.
- **Images** only keep `data:image/...` inline sources.
- The viewer uses a sans-serif font for HTML and Markdown so pages do not inherit Micron monospace chrome. Override colours and typography with your own CSS.

## Mesh Server API

- `POST /api/v1/page-nodes/{node_id}/pages` with `name` and `content` saves a page. Invalid extensions return HTTP 400 with a short message.
- Listed pages only include files with allowed extensions in the `pages/` directory.

## Archives

Snapshots in **Archives** use the same rendering pipeline as the Nomad browser. The archived `page_path` extension selects Micron, Markdown, text, or HTML handling. Exports keep the original extension when it is `.mu`, `.md`, `.txt`, or `.html`.

## See also

- **Nomad Network and Mesh Server** for browsing and hosting workflows
- **Architecture and design** for where page nodes fit in the backend
- Default Nomad entry path remains `/page/index.mu` unless you change the URL in the browser
