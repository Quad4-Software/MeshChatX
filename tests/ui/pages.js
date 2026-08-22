/**
 * UI page catalog for smoke + Lighthouse audits.
 * Paths are Vue hash routes (without the leading #).
 * Lighthouse always runs against production-built assets (playwright.lighthouse.config.js).
 */

const DEFAULT_BUDGETS = {
    performance: 50,
    accessibility: 75,
    "best-practices": 70,
};

/**
 * @typedef {object} UiPage
 * @property {string} id stable id for reports
 * @property {string} path hash route path, e.g. /messages
 * @property {string|RegExp} ready locator text or role used to confirm paint
 * @property {"heading"|"text"|"placeholder"|"role"} [readyKind]
 * @property {string} [readyName] for role locators
 * @property {boolean} [ci] include in CI lighthouse subset
 * @property {Partial<typeof DEFAULT_BUDGETS>} [budgets]
 */

/** @type {UiPage[]} */
const UI_PAGES = [
    {
        id: "messages",
        path: "/messages",
        readyKind: "placeholder",
        ready: /Search \d+ conversations/i,
        ci: true,
        budgets: { performance: 45 },
    },
    {
        id: "contacts",
        path: "/contacts",
        readyKind: "heading",
        ready: "Contacts",
        ci: true,
    },
    {
        id: "interfaces",
        path: "/interfaces",
        readyKind: "role",
        readyName: /Add Interface/i,
        ready: "link",
        ci: true,
    },
    {
        id: "settings",
        path: "/settings",
        readyKind: "text",
        ready: "Profile",
        ci: true,
        budgets: { performance: 45 },
    },
    {
        id: "propagation-nodes",
        path: "/propagation-nodes",
        readyKind: "text",
        ready: "Hosted node",
        ci: true,
    },
    {
        id: "map",
        path: "/map",
        readyKind: "heading",
        ready: "Map",
        budgets: { performance: 40 },
    },
    {
        id: "identities",
        path: "/identities",
        readyKind: "heading",
        ready: "Identities",
    },
    {
        id: "ping",
        path: "/ping",
        readyKind: "text",
        ready: "Ping Mesh Peers",
    },
    {
        id: "documentation",
        path: "/documentation",
        readyKind: "heading",
        ready: "Documentation",
    },
    {
        id: "about",
        path: "/about",
        readyKind: "text",
        ready: "Active sessions",
    },
    {
        id: "tools",
        path: "/tools",
        readyKind: "text",
        ready: "Utilities",
    },
    {
        id: "network-visualiser",
        path: "/network-visualiser",
        readyKind: "text",
        ready: "Reticulum Mesh",
        budgets: { performance: 35 },
    },
    {
        id: "archives",
        path: "/archives",
        readyKind: "placeholder",
        ready: "Search nodes or content...",
    },
    {
        id: "blocked",
        path: "/blocked",
        readyKind: "heading",
        ready: "Banished",
    },
];

function budgetsFor(page) {
    return { ...DEFAULT_BUDGETS, ...(page.budgets || {}) };
}

function pagesForCi() {
    return UI_PAGES.filter((p) => p.ci);
}

function resolvePages(opts = {}) {
    if (opts.ciOnly) {
        return pagesForCi();
    }
    if (opts.ids && opts.ids.length > 0) {
        const want = new Set(opts.ids);
        return UI_PAGES.filter((p) => want.has(p.id));
    }
    return UI_PAGES.slice();
}

module.exports = {
    DEFAULT_BUDGETS,
    UI_PAGES,
    budgetsFor,
    pagesForCi,
    resolvePages,
};
