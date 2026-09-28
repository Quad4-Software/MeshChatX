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
 * Observed (unthrottled) budgets for tests/ui/perf.spec.js. These guard
 * real regressions, not absolute speed: cold FCP/LCP on a cache-disabled
 * first load, SPA hash-route transition latency, and post-mount JS heap.
 * Generous defaults keep shared CI runners from flapping. Tighten per page
 * only after a few recorded runs.
 */
const DEFAULT_PERF_BUDGETS = {
    fcpMs: 4000,
    lcpMs: 6000,
    domContentLoadedMs: 4000,
    loadMs: 9000,
    navMs: 5000,
    heapMb: 250,
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
 * @property {Partial<typeof DEFAULT_PERF_BUDGETS>} [perf]
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
        id: "call",
        path: "/call",
        readyKind: "text",
        ready: "Phonebook",
    },
    {
        id: "relay-chat",
        path: "/relay-chat",
        readyKind: "role",
        ready: "tab",
        readyName: /Connect/i,
    },
    {
        id: "nomadnetwork",
        path: "/nomadnetwork",
        readyKind: "placeholder",
        ready: /favourites/i,
    },
    {
        id: "bots",
        path: "/bots",
        readyKind: "heading",
        ready: "LXMFy Bots",
    },
    {
        id: "map",
        path: "/map",
        readyKind: "role",
        ready: "tab",
        readyName: /Map/,
        budgets: { performance: 40 },
        perf: { lcpMs: 8000, heapMb: 350 },
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
        readyKind: "placeholder",
        ready: "Search documentation...",
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
        readyKind: "placeholder",
        ready: "Search tools...",
    },
    {
        id: "network-visualiser",
        path: "/network-visualiser",
        readyKind: "text",
        ready: "Reticulum Mesh",
        budgets: { performance: 35 },
        perf: { lcpMs: 8000, navMs: 8000, heapMb: 350 },
    },
    {
        id: "archives",
        path: "/archives",
        readyKind: "placeholder",
        ready: "Search content, node name, hash, or path...",
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

function perfBudgetsFor(page) {
    return { ...DEFAULT_PERF_BUDGETS, ...(page.perf || {}) };
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
    DEFAULT_PERF_BUDGETS,
    UI_PAGES,
    budgetsFor,
    perfBudgetsFor,
    pagesForCi,
    resolvePages,
};
