const { test, expect } = require("@playwright/test");
const { prepareE2eSession } = require("./helpers");

// Action buttons must look like buttons, not pills: compact height on
// desktop, a small border radius, and 44px targets on touch viewports.

const TEXT_BUTTON = "button.primary-chip, button.secondary-chip, button.danger-chip";

async function openPropagationNodes(page) {
    await page.goto("/#/propagation-nodes");
    await page.waitForSelector(TEXT_BUTTON, { timeout: 30000 });
}

function measureButtons(page) {
    return page.locator(TEXT_BUTTON).evaluateAll((els) =>
        els.map((el) => {
            const r = el.getBoundingClientRect();
            const cs = getComputedStyle(el);
            return { h: r.height, radius: parseFloat(cs.borderTopLeftRadius), w: r.width };
        })
    );
}

test.describe("action button shape", () => {
    test.beforeEach(async ({ page }) => {
        await prepareE2eSession(page.request);
    });

    test("desktop buttons are compact and squarish at 1280", async ({ page }) => {
        await page.setViewportSize({ width: 1280, height: 800 });
        await openPropagationNodes(page);
        const buttons = page.locator(TEXT_BUTTON);
        const count = await buttons.count();
        expect(count).toBeGreaterThan(0);
        for (const m of await measureButtons(page)) {
            expect(m.h).toBeLessThanOrEqual(36);
            expect(m.radius).toBeLessThan(10);
        }
    });

    test("touch viewport keeps 44px targets at 390", async ({ browser }) => {
        const context = await browser.newContext({
            viewport: { width: 390, height: 844 },
            hasTouch: true,
            isMobile: true,
        });
        const page = await context.newPage();
        await prepareE2eSession(page.request);
        await openPropagationNodes(page);
        const buttons = page.locator(TEXT_BUTTON);
        const count = await buttons.count();
        expect(count).toBeGreaterThan(0);
        for (const m of await measureButtons(page)) {
            expect(m.h).toBeGreaterThanOrEqual(44);
            expect(m.radius).toBeLessThan(10);
        }
        await context.close();
    });

    test("source guard: no pill-shaped text action buttons", async () => {
        // Scan style.css shared action classes and confirm none use
        // rounded-full on a text-sized button any more.
        const fs = require("node:fs");
        const path = require("node:path");
        const css = fs.readFileSync(path.join(__dirname, "../../meshchatx/src/frontend/style.css"), "utf8");
        for (const cls of [
            "primary-chip",
            "secondary-chip",
            "danger-chip",
            "primary-action",
            "secondary-action",
            "danger-action",
        ]) {
            const block = css.match(new RegExp(`\\.${cls} \\{[^}]*\\}`));
            expect(block, `${cls} block missing`).toBeTruthy();
            expect(block[0]).not.toContain("rounded-full");
        }
    });
});
