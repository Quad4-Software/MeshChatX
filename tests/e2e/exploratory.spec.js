const { test, expect } = require("@playwright/test");
const { prepareE2eSession } = require("./helpers");

// Exploratory route crawl: visits every non-popout application route,
// follows in-app navigation links a bounded number of hops, and fails on
// any uncaught pageerror or console error. This is the cheap version of
// agentic exploration: broad UI coverage without hand-written scenarios.

const ROUTES = [
    "/",
    "/about",
    "/interfaces",
    "/interfaces/add",
    "/messages",
    "/contacts",
    "/map",
    "/network-visualiser",
    "/relay-chat",
    "/archives",
    "/propagation-nodes",
    "/ping",
    "/rncp",
    "/rns-filesync",
    "/rnsh",
    "/rnx",
    "/rnstatus",
    "/rnpath",
    "/rnpath-trace",
    "/rnprobe",
    "/translator",
    "/bots",
    "/bots/new",
    "/forwarder",
    "/micron-editor",
    "/tools/reticulum-config-editor",
    "/mesh-server",
    "/documentation",
    "/profile/icon",
    "/settings",
    "/identities",
    "/blocked",
    "/tools",
    "/licenses",
    "/tools/paper-message",
    "/tools/nearby",
    "/tools/sieve-filters",
    "/tools/message-blocklist",
    "/tools/rnode-flasher",
    "/tools/repository-server",
    "/debug/logs",
    "/changelog",
];

const IGNORED_CONSOLE_ERRORS = [
    /net::ERR_/i, // expected offline fetch failures
    /failed to fetch/i,
    /WebSocket/i, // ws reconnect noise while the backend settles
    /404/,
];

test.describe("Exploratory route crawl", () => {
    test.setTimeout(600000);
    test.describe.configure({ mode: "serial" });

    test.beforeEach(async ({ request }) => {
        await prepareE2eSession(request);
    });

    test("every route loads without pageerrors or console errors", async ({ page }) => {
        const errors = [];
        page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
        page.on("console", (msg) => {
            if (msg.type() !== "error") {
                return;
            }
            const text = msg.text();
            if (!IGNORED_CONSOLE_ERRORS.some((re) => re.test(text))) {
                errors.push(`console: ${text}`);
            }
        });

        const visited = [];
        for (const route of ROUTES) {
            errors.length = 0;
            await page.goto(`/#${route}`, { waitUntil: "domcontentloaded" });
            await page.waitForTimeout(1500);
            // The app shell should render something, not a blank frame.
            const bodyText = await page
                .locator("body")
                .innerText()
                .catch(() => "");
            expect(bodyText.trim().length, `route ${route} rendered an empty body`).toBeGreaterThan(0);
            expect(errors, `route ${route}`).toEqual([]);
            visited.push(route);
        }
        expect(visited.length).toBe(ROUTES.length);
    });

    test("in-app navigation links stay inside the app without errors", async ({ page }) => {
        const errors = [];
        page.on("pageerror", (e) => errors.push(e.message));
        page.on("console", (msg) => {
            if (msg.type() === "error" && !IGNORED_CONSOLE_ERRORS.some((re) => re.test(msg.text()))) {
                errors.push(msg.text());
            }
        });

        // Seed on a content-rich page, then follow visible navigation links.
        await page.goto("/#/messages", { waitUntil: "domcontentloaded" });
        await page.waitForTimeout(1500);

        const hops = 12;
        const seen = new Set(["#/messages"]);
        for (let i = 0; i < hops; i++) {
            const links = await page.locator('a[href^="#/"]:visible, a[href*="/#/"]:visible').all();
            if (!links.length) {
                break;
            }
            // Deterministic pick: first unseen link, else first link.
            let target = null;
            for (const link of links) {
                const href = await link.getAttribute("href").catch(() => null);
                if (!href) {
                    continue;
                }
                const norm = href.replace(/^[^#]*#/, "#");
                if (!seen.has(norm)) {
                    target = link;
                    seen.add(norm);
                    break;
                }
            }
            target = target || links[0];
            await target.click().catch(() => {});
            await page.waitForTimeout(800);
        }
        expect(seen.size).toBeGreaterThan(2);
        expect(errors).toEqual([]);
    });
});
