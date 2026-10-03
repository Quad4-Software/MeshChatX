/**
 * Declarative guide catalog for docs screenshots/clips.
 *
 * Each guide produces one or more annotated stills (.webp) and optional
 * animated clips (.webp/.gif) under docs/assets/guides/<id>/.
 *
 * Guide:
 *   id       guide slug -> docs/assets/guides/<id>/
 *   path     hash route ("/messages/...")
 *   ready    ready signal (see tests/ui/ready.js kinds)
 *   readyKind, readyName   for role locators
 *   themes   themes to capture (default ["dark"])
 *   factor   "desktop" | "mobile" (default "desktop")
 *   shots    [{ name, actions?(page), annotations, caption? }]
 *   clips    [{ name, actions(page), fps?, format?: "webp"|"gif" }]
 *
 * actions run before the shot/clip is captured; annotations use
 * applyGuideAnnotations kinds (box, spotlight, blur, arrow, caption).
 */

const GUIDES = [
    {
        id: "compose-message",
        path: "/messages",
        readyKind: "placeholder",
        ready: /Search \d+ conversations/i,
        themes: ["dark"],
        factor: "desktop",
        shots: [
            {
                name: "01-overview",
                annotations: [
                    { kind: "caption", text: "The Messages home", sub: "Conversations on the left, chat pane on the right", pos: "bottom" },
                    { selector: "text=Conversations", kind: "box", note: "Your conversation list", notePos: "right" },
                    { selector: "text=Compose", kind: "box", badge: 1 },
                ],
            },
            {
                name: "02-compose",
                annotations: [
                    { selector: "text=Compose", kind: "spotlight", note: "Click Compose to start a new conversation", notePos: "bottom" },
                ],
            },
        ],
        clips: [
            {
                name: "compose-open",
                format: "webp",
                fps: 8,
                actions: async (page) => {
                    await page.getByText("Compose", { exact: false }).first().click().catch(() => {});
                    await page.waitForTimeout(1200);
                },
            },
        ],
    },
    {
        id: "settings-appearance",
        path: "/settings",
        readyKind: "text",
        ready: "Appearance",
        themes: ["dark"],
        factor: "desktop",
        shots: [
            {
                name: "01-settings",
                annotations: [
                    { kind: "caption", text: "Settings", sub: "Appearance, fonts, and theme controls", pos: "top" },
                    { selector: "h2:has-text('Appearance')", kind: "box", badge: 1, note: "Theme and font settings", notePos: "right" },
                ],
            },
        ],
    },
    {
        id: "contacts-add",
        path: "/contacts",
        readyKind: "text",
        ready: "Ada Lovelace",
        themes: ["dark", "light"],
        factor: "desktop",
        shots: [
            {
                name: "01-contacts",
                annotations: [
                    { kind: "caption", text: "Contacts", sub: "Pinned peers and favourites", pos: "top" },
                    { selector: "text=Ada Lovelace", kind: "box", note: "A synced contact", notePos: "right" },
                ],
            },
        ],
    },
];

module.exports = { GUIDES };
