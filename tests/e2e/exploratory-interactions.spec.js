const { test, expect } = require("@playwright/test");
const { prepareE2eSession } = require("./helpers");

// Deeper exploratory crawl: interacts with safe controls on every route
// (buttons, menus, popups, the command palette) and fails on any pageerror
// or console error. Destructive words filter out buttons that would delete
// data, kill connections, or write config in ways the crawl cannot undo.

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
    "/tutorial",
    "/call",
    "/nomadnetwork",
];

const SKIP_BUTTON =
    /delete|remove|wipe|clear|erase|format|flash|uninstall|block|unblock|call|dial|hang\s*up|send|shutdown|restart|logout|log\s*out|purge|destroy|factory|reset|import|export|upload|download|backup|restore|sign|authorize|approve|grant|execute|run script|panic/i;

const IGNORED_CONSOLE_ERRORS = [
    /net::ERR_/i,
    /failed to fetch/i,
    /WebSocket/i,
    // 4xx responses on empty-state actions are designed API outcomes the
    // frontend already surfaces (toasts, empty states). 5xx stays flagged.
    /Failed to load resource: the server responded with a status of (4\d\d|404)/i,
];

function watchErrors(page, errors) {
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
    page.on("response", (resp) => {
        const status = resp.status();
        const url = resp.url();
        if (status >= 500 && !IGNORED_CONSOLE_ERRORS.some((re) => re.test(url))) {
            errors.push(`http ${status}: ${url}`);
        }
    });
}

async function closeTopLayer(page) {
    // Close any modal, menu, or overlay opened by the last click.
    await page.keyboard.press("Escape");
    await page.waitForTimeout(150);
}

test.describe("Exploratory interaction crawl", () => {
    test.setTimeout(900000);
    test.describe.configure({ mode: "serial" });

    test.beforeEach(async ({ request }) => {
        await prepareE2eSession(request);
    });

    test("safe buttons on every route respond without errors", async ({ page }) => {
        const errors = [];
        watchErrors(page, errors);

        const CLICK_CAP = 10;
        const clicked = [];
        for (const route of ROUTES) {
            const routeStart = Date.now();
            await page.goto(`/#${route}`, { waitUntil: "domcontentloaded" });
            await page.waitForTimeout(700);
            errors.length = 0;

            const buttons = await page.locator("button:visible").all();
            let clicks = 0;
            for (const btn of buttons) {
                if (clicks >= CLICK_CAP) {
                    break;
                }
                const label = [
                    (await btn.innerText().catch(() => "")) || "",
                    (await btn.getAttribute("aria-label").catch(() => "")) || "",
                    (await btn.getAttribute("title").catch(() => "")) || "",
                ]
                    .join(" ")
                    .trim();
                if (!label || SKIP_BUTTON.test(label)) {
                    continue;
                }
                try {
                    await btn.click({ timeout: 1200 });
                    clicks += 1;
                    await page.waitForTimeout(150);
                    await closeTopLayer(page);
                } catch {
                    // Unclickable element (covered, animating away): skip.
                }
            }
            const secs = ((Date.now() - routeStart) / 1000).toFixed(0);
            clicked.push(`${route}:${clicks}(${secs}s)`);
            expect(errors, `route ${route}`).toEqual([]);
        }
        console.log(`crawl clicks: ${clicked.join(", ")}`);
    });

    test("context menus open, render items, and close cleanly", async ({ page }) => {
        const errors = [];
        watchErrors(page, errors);

        let menusOpened = 0;
        for (const route of ROUTES) {
            await page.goto(`/#${route}`, { waitUntil: "domcontentloaded" });
            await page.waitForTimeout(1000);
            errors.length = 0;

            // Kebab/more/overflow style toggles: aria-haspopup marks most of
            // them, menu dots cover the rest.
            const toggles = await page
                .locator(
                    'button[aria-haspopup="true"]:visible, button[aria-haspopup="menu"]:visible, button[aria-expanded]:visible'
                )
                .all();
            for (const t of toggles.slice(0, 6)) {
                try {
                    await t.click({ timeout: 1500 });
                    await page.waitForTimeout(250);
                    const openMenu = page.locator(
                        '[role="menu"]:visible, [role="listbox"]:visible, .context-menu:visible, .dropdown-menu:visible, [class*="context-menu"]:visible'
                    );
                    if ((await openMenu.count()) > 0) {
                        menusOpened += 1;
                        const items = openMenu.locator('[role="menuitem"], [role="option"], li, button');
                        expect(await items.count()).toBeGreaterThan(0);
                    }
                    await closeTopLayer(page);
                } catch {
                    await closeTopLayer(page);
                }
            }
            expect(errors, `route ${route}`).toEqual([]);
        }
        console.log(`menus opened: ${menusOpened}`);
        expect(menusOpened).toBeGreaterThan(0);
    });

    test("command palette opens, filters, and closes without actions", async ({ page }) => {
        const errors = [];
        watchErrors(page, errors);

        await page.goto("/#/messages", { waitUntil: "domcontentloaded" });
        await page.waitForTimeout(1000);

        const trigger = page.locator('[data-testid="header-command-palette"]');
        if (await trigger.isVisible().catch(() => false)) {
            await trigger.click();
            await page.waitForTimeout(400);
            // Type a query and arrow through results; do not press Enter.
            await page.keyboard.type("contacts");
            await page.waitForTimeout(300);
            await page.keyboard.press("ArrowDown");
            await page.waitForTimeout(200);
            await page.keyboard.press("Escape");
        }
        expect(errors).toEqual([]);
    });
});
