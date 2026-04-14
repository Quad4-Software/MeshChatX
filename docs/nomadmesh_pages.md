# NomadNet Network browser and Mesh Server pages

MeshChatX can serve pages from a **Mesh Server** (local Reticulum page node) found in the tools section and display them in the **NomadNet** browser. Pages are fetched over the usual Nomad path convention: `/page/<filename>`.

## Supported filenames

| Extension | Role                                                         |
| --------- | ------------------------------------------------------------ |
| `.mu`     | **Micron** markup (NomadNet default).                        |
| `.md`     | **Markdown** (GitHub-flavored features via the renderer).    |
| `.txt`    | **Plain text** (shown escaped, monospace-friendly wrapping). |
| `.html`   | **Static HTML** with **CSS only** (see security below).      |

If you add a page without a recognised extension, the server stores it as **`.mu`**. Filenames with other extensions (for example `.exe`) are rejected when saving through the API.

## Plain text (`.txt`)

Content is **HTML-escaped** and shown with **pre-wrapped** whitespace. There is no Markdown parsing on `.txt` pages.

## Markdown (`.md`)

- **Not the same engine as chat:** Conversations use the lightweight **`MarkdownRenderer`** (HTML-escaped first, then patterns for headers, bold, code, links). Nomad **`.md`** pages use **`marked`** (GFM-oriented) plus sanitisation, so features and edge cases can differ. Automated tests cover both paths.
- Use **ATX headings** with a hash and a **space** before the title, for example `# Title`, `## Section`, `#### Subsection`. CommonMark requires that space; MeshChatX may normalise some common shorthand forms, but relying on the standard form is safest.
- Line breaks and spacing: the viewer preserves wrapping behaviour suitable for technical text; fenced code blocks keep indentation.
- Links are **sanitised**: off-mesh `http`/`https` links in rendered content are removed or restricted so the preview cannot drive external navigation without mesh-style URLs.

## HTML (`.html`)

- **JavaScript** is not executed: `script` tags and event-handler attributes are stripped.
- **External resources** are blocked where possible: `@import` and `url(...)` pointing at `http://`, `https://`, or protocol-relative URLs are removed from CSS. Embedded `<style>` blocks are kept; rules that target `html` or `body` are **rewritten** to apply to the viewer’s root container so your layout still applies.
- **Links**: `href` values that are not mesh-style (`:` paths, 32-character hex prefixes, `/page/...`, `/file/...`, or `#` fragments) are removed. Images only keep `data:image/...` sources for inline images.
- The viewer uses a **sans-serif** font for HTML and Markdown so pages do not inherit the monospace Micron chrome. You can override colours and typography with your own CSS.

## Mesh Server API

- `POST /api/v1/page-nodes/{node_id}/pages` with `name` and `content` saves a page; invalid extensions return **400** with a short message.
- Listed pages only include files with allowed extensions in the `pages/` directory.

## Archives

Snapshots in **Archives** use the same rendering pipeline as the Nomad browser (Micron, Markdown, text, sanitised HTML) using the archived `page_path` to pick the format. Exports keep the original extension when it is `.mu`, `.md`, `.txt`, or `.html`.

## See also

- Architecture overview: `meshchatx.md` in this docs bundle.
- Default Nomad entry path remains `/page/index.mu` unless you change the URL in the browser.
