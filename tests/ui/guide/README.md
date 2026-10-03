# Guide captures

Programmatic docs screenshots and clips with annotation overlays.

## Run

```bash
# start the e2e stack first (prod bundle gives the most accurate shots)
MESHCHAT_UI_PROD=1 MESHCHAT_LH_SKIP_BUILD=1 bash scripts/ui/start-ui-stack.sh

# capture everything in the catalog
MESHCHAT_UI_PROD=1 pnpm run test:ui:guides

# or a subset
MESHCHAT_UI_PROD=1 MESHCHAT_GUIDE_IDS=compose-message pnpm run test:ui:guides
```

Output lands in `docs/assets/guides/<id>/` as `<shot>-<theme>.webp` and
`<clip>-<theme>.webp` (animated). Reference them from docs markdown with a
relative path, e.g. from `docs/en/messaging.md`:

```markdown
![The Messages home](../assets/guides/compose-message/01-overview-dark.webp)
```

The backend rewrites relative image srcs to `/meshchatx-docs/<lang>/...` so
images render in-app while staying relative for repository readers.

## Authoring a guide

Add an entry to `tests/ui/guide/guides.js`:

```js
{
    id: "my-guide",
    path: "/settings",
    readyKind: "text",
    ready: "Appearance",
    themes: ["dark"],          // or ["light", "dark"]
    factor: "desktop",         // or "mobile"
    shots: [
        {
            name: "01-name",
            // optional actions run before the capture
            actions: async (page) => { await page.click("text=Compose"); },
            annotations: [
                { kind: "caption", text: "Title", sub: "subtitle", pos: "top" },
                { selector: "h2:has-text('Appearance')", kind: "box",
                  badge: 1, note: "Step text", notePos: "right" },
            ],
        },
    ],
    clips: [
        {
            name: "flow",
            format: "webp",        // or "gif"
            fps: 8,
            actions: async (page) => { ... },
        },
    ],
}
```

## Annotation kinds

| kind        | effect                                                     |
| ----------- | ---------------------------------------------------------- |
| `box`       | accent ring around the element, `badge` adds a step number |
| `spotlight` | dims everything except the target                          |
| `blur`      | backdrop blur over the element (redact private data)       |
| `arrow`     | arrow into the element, `from: top|bottom|left|right`      |
| `caption`   | floating card, `pos: top|bottom`, optional `sub`           |

Selectors are Playwright selectors resolved via `boundingBox()`, so
`text=`, `role=`, css, `:has-text()` etc. all work. Prefer exact or scoped
selectors: bare `text=Foo` can hit an ancestor or a substring in nav
labels. Missing selectors warn but do not fail the capture.

Annotations read `--mc-*` CSS vars at runtime, so colors track the theme the
shot is captured in.

## Clips

`startGuideRecording(page)` records the page via CDP screencast while
`actions` run, then `rec.save(file)` assembles frames into animated WebP
(default) or GIF through ffmpeg.
