/**
 * Screenshot catalog for the automated screenshot tool.
 * Each entry maps to one png per viewport in screenshots/.
 * Paths are Vue hash routes (without the leading #).
 */

const { E2E_SCROLL_PEER_HASH } = require("../e2e/helpers");

const VIEWPORTS = {
    desktop: { width: 1440, height: 900 },
    mobile: { width: 412, height: 915 },
};

/**
 * @typedef {object} ScreenshotEntry
 * @property {string} id file base name, e.g. messages -> screenshots/messages.png
 * @property {string} path hash route path
 * @property {string|RegExp} ready ready signal (see ready.js kinds)
 * @property {"heading"|"text"|"placeholder"|"role"} [readyKind]
 * @property {string} [readyName] for role locators
 * @property {boolean} [mobile] also capture the mobile viewport
 * @property {number} [settleMs] extra settle time for animations/map tiles
 */

/** @type {ScreenshotEntry[]} */
const SCREENSHOT_PAGES = [
    {
        id: "messages",
        path: "/messages",
        readyKind: "placeholder",
        ready: /Search \d+ conversations/i,
        mobile: true,
    },
    {
        id: "conversation",
        path: `/messages/${E2E_SCROLL_PEER_HASH}`,
        readyKind: "placeholder",
        ready: /^Message for/i,
        mobile: true,
        settleMs: 500,
    },
    {
        id: "contacts",
        path: "/contacts",
        readyKind: "text",
        ready: "Ada Lovelace",
        mobile: true,
    },
    {
        id: "relay-chat",
        path: "/relay-chat",
        readyKind: "role",
        ready: "tab",
        readyName: /Connect/i,
        mobile: true,
    },
    {
        id: "call",
        path: "/call",
        readyKind: "text",
        ready: "Phonebook",
        mobile: true,
    },
    {
        id: "map",
        path: "/map",
        readyKind: "text",
        ready: "Online Mode",
        mobile: true,
        settleMs: 1500,
    },
    {
        id: "interfaces",
        path: "/interfaces",
        readyKind: "role",
        ready: "link",
        readyName: /Add Interface/i,
        mobile: true,
    },
    {
        id: "settings",
        path: "/settings",
        readyKind: "text",
        ready: "Profile",
        mobile: true,
    },
    {
        id: "documentation",
        path: "/documentation",
        readyKind: "heading",
        ready: "Getting started with MeshChatX",
        mobile: true,
        settleMs: 800,
    },
    {
        id: "tools",
        path: "/tools",
        readyKind: "placeholder",
        ready: /Search tools/i,
    },
    {
        id: "bots",
        path: "/bots",
        readyKind: "heading",
        ready: "LXMFy Bots",
        mobile: true,
    },
    {
        id: "identities",
        path: "/identities",
        readyKind: "heading",
        ready: "Identities",
    },
    {
        id: "propagation-nodes",
        path: "/propagation-nodes",
        readyKind: "text",
        ready: "Hosted node",
    },
    {
        id: "archives",
        path: "/archives",
        readyKind: "placeholder",
        ready: "Search content, node name, hash, or path...",
    },
    {
        id: "network-visualiser",
        path: "/network-visualiser",
        readyKind: "text",
        ready: "Reticulum Mesh",
        settleMs: 1200,
    },
    {
        id: "nomadnetwork",
        path: "/nomadnetwork",
        readyKind: "placeholder",
        ready: /favourites/i,
        mobile: true,
    },
    {
        id: "blocked",
        path: "/blocked",
        readyKind: "heading",
        ready: "Banished",
    },
    {
        id: "reticulum-config-editor",
        path: "/tools/reticulum-config-editor",
        readyKind: "text",
        ready: "Reticulum Config Editor",
        mobile: true,
    },
    {
        id: "about",
        path: "/about",
        readyKind: "text",
        ready: "Active sessions",
    },
];

function resolveShots(opts = {}) {
    if (opts.ids && opts.ids.length > 0) {
        const want = new Set(opts.ids);
        return SCREENSHOT_PAGES.filter((p) => want.has(p.id));
    }
    return SCREENSHOT_PAGES.slice();
}

module.exports = {
    SCREENSHOT_PAGES,
    VIEWPORTS,
    resolveShots,
};
