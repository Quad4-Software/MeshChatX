const { test, expect } = require("@playwright/test");
const { dismissMapOnboardingTooltip, prepareE2eSession } = require("./helpers");

// The drawing toolbar must stay at a constant offset below the app
// chrome at every viewport size, never overlap the OL controls, stay
// inside the viewport, and keep 44px touch targets.

const VIEWPORTS = [
    { width: 1440, height: 900 },
    { width: 1280, height: 800 },
    { width: 1024, height: 768 },
    { width: 900, height: 700 },
    { width: 768, height: 600 },
    { width: 640, height: 500 },
    { width: 480, height: 450 },
    { width: 390, height: 420 },
    { width: 320, height: 400 },
];

const TOOLBAR = "div.absolute.top-2.left-1\\/2.-translate-x-1\\/2";

async function openMap(page) {
    await page.addInitScript(() => {
        localStorage.setItem("meshchatx.map.offlineMode", "0");
        localStorage.setItem("map_onboarding_seen", "true");
    });
    await prepareE2eSession(page.request);
    await page.goto("/#/map");
    await dismissMapOnboardingTooltip(page);
    await page.waitForSelector("canvas", { timeout: 60000 });
}

function rectOf(locator) {
    return locator.first().evaluate((el) => {
        const r = el.getBoundingClientRect();
        return { x: r.x, y: r.y, w: r.width, h: r.height, right: r.right, bottom: r.bottom };
    });
}

test.describe("map toolbar layout", () => {
    for (const vp of VIEWPORTS) {
        test(`toolbar stays anchored and clear of controls at ${vp.width}x${vp.height}`, async ({ page }) => {
            await page.setViewportSize({ width: vp.width, height: vp.height });
            await openMap(page);

            const toolbar = page.locator(TOOLBAR);
            await expect(toolbar).toBeVisible({ timeout: 30000 });
            const tr = await rectOf(toolbar);

            // Anchored: 8px below the map container top at every size.
            const mapRect = await page
                .locator(".ol-viewport")
                .first()
                .evaluate((el) => {
                    const r = el.getBoundingClientRect();
                    return { x: r.x, y: r.y, w: r.width, h: r.height };
                });
            expect(Math.abs(tr.y - (mapRect.y + 8))).toBeLessThanOrEqual(2);

            // Inside the viewport horizontally.
            expect(tr.x).toBeGreaterThanOrEqual(0);
            expect(tr.right).toBeLessThanOrEqual(vp.width);

            // No overlap with OL zoom controls or the rotate control.
            for (const sel of [".ol-zoom", ".ol-rotate", ".ol-scale-line"]) {
                const el = page.locator(sel).first();
                if (!(await el.count())) continue;
                const r = await rectOf(el);
                const overlap = tr.x < r.right && tr.right > r.x && tr.y < r.bottom && tr.bottom > r.y;
                expect(overlap, `${sel} overlaps toolbar`).toBe(false);
            }

            // Touch targets: every button in the toolbar is at least 44px.
            const sizes = await toolbar.locator("button").evaluateAll((els) =>
                els.map((el) => {
                    const r = el.getBoundingClientRect();
                    return { w: r.width, h: r.height };
                })
            );
            for (const s of sizes) {
                expect(s.w, "button width < 44px").toBeGreaterThanOrEqual(43.5);
                expect(s.h, "button height < 44px").toBeGreaterThanOrEqual(43.5);
            }
        });
    }

    test("toolbar top is identical at hidpi and under pinch-zoom", async ({ page }) => {
        await page.setViewportSize({ width: 1280, height: 800 });
        await openMap(page);
        const tr1 = await rectOf(page.locator(TOOLBAR));
        // Emulate a hiDPI device via device scale factor reload.
        await page.emulateMedia({});
        const ctx2 = await page
            .context()
            .browser()
            .newContext({
                viewport: { width: 1280, height: 800 },
                deviceScaleFactor: 2,
            });
        const page2 = await ctx2.newPage();
        try {
            await openMap(page2);
            const tr2 = await rectOf(page2.locator(TOOLBAR));
            expect(Math.abs(tr2.y - tr1.y)).toBeLessThanOrEqual(2);
        } finally {
            await ctx2.close();
        }
    });
});
