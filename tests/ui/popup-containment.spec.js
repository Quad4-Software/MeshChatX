// SPDX-License-Identifier: 0BSD
// Dropdown and popup containment: opens every DropDownMenu trigger on each
// key page and asserts the anchored panel (and its caret, when present)
// stays inside the viewport without clipping.
const { test, expect } = require("@playwright/test");

const WIDTHS = [360, 390, 1280];

const PAGES = [
    { route: "/#/nomadnetwork", label: "announces/nomadnet" },
    { route: "/#/map", label: "map" },
    { route: "/#/settings", label: "settings" },
    { route: "/#/messages", label: "messages" },
];

async function dismissFirstRun(page) {
    await page.goto("/#/", { waitUntil: "domcontentloaded" });
    await page
        .evaluate(() => {
            const skip = [...document.querySelectorAll(".tutorial-action-btn-ghost")][0];
            if (skip) skip.click();
            document.querySelectorAll(".modal-panel").forEach((p) => {
                const btn = p.querySelector(".modal-panel__header button");
                if (btn) btn.click();
            });
        })
        .catch(() => {});
    await page.waitForTimeout(800);
}

async function openAllDropdowns(page, label) {
    // DropDownMenu renders the trigger inside .touch-manipulation.
    const triggers = page.locator(".touch-manipulation");
    const count = await triggers.count();
    const results = [];
    for (let i = 0; i < count; i++) {
        const trig = triggers.nth(i);
        if (!(await trig.isVisible().catch(() => false))) continue;
        await trig.click({ force: true }).catch(() => {});
        await page.waitForTimeout(400);
        const panel = page.locator(".dropdown-panel").first();
        const visible = await panel.isVisible().catch(() => false);
        if (!visible) continue;
        const r = await panel.evaluate((el) => {
            const rect = el.getBoundingClientRect();
            const caret = document.querySelector(".dropdown-caret");
            const cr = caret ? caret.getBoundingClientRect() : null;
            const vw = window.innerWidth;
            const vh = window.innerHeight;
            return {
                left: rect.left,
                right: rect.right,
                top: rect.top,
                bottom: rect.bottom,
                vw,
                vh,
                caret: cr ? { left: cr.left, right: cr.right, top: cr.top, bottom: cr.bottom } : null,
            };
        });
        const clipped = r.left < -1 || r.top < -1 || r.right > r.vw + 1 || r.bottom > r.vh + 1;
        const caretClipped =
            r.caret && (r.caret.left < -1 || r.caret.top < -1 || r.caret.right > r.vw + 1 || r.caret.bottom > r.vh + 1);
        results.push({
            idx: i,
            clipped,
            caretClipped,
            rect: { left: r.left, right: r.right, vw: r.vw },
        });
        // close before trying the next trigger
        await page.keyboard.press("Escape").catch(() => {});
        await page.mouse.click(5, 5).catch(() => {});
        await page.waitForTimeout(250);
    }
    const bad = results.filter((r) => r.clipped || r.caretClipped);
    expect(bad, `${label}: clipped dropdown panels ${JSON.stringify(bad)}`).toEqual([]);
}

test.describe("popup containment", () => {
    for (const p of PAGES) {
        for (const w of WIDTHS) {
            test(`${p.label} dropdowns stay in viewport at ${w}px`, async ({ page }) => {
                test.setTimeout(120000);
                await page.setViewportSize({ width: w, height: w >= 1280 ? 800 : 700 });
                await dismissFirstRun(page);
                await page.goto(p.route, { waitUntil: "domcontentloaded" });
                await page.waitForTimeout(3000);
                await openAllDropdowns(page, `${p.label} ${w}px`);
            });
        }
    }

    for (const w of WIDTHS) {
        test(`map settings panel stays in viewport at ${w}px`, async ({ page }) => {
            await page.setViewportSize({ width: w, height: w >= 1280 ? 800 : 700 });
            await dismissFirstRun(page);
            await page.goto("/#/map", { waitUntil: "domcontentloaded" });
            await page.waitForTimeout(3000);
            const gear = page.locator(`button[title*="etting"], button[aria-label*="etting"]`).first();
            if (!(await gear.count())) return;
            await gear.click({ force: true }).catch(() => {});
            await page.waitForTimeout(600);
            const rect = await page.evaluate(() => {
                const panels = [...document.querySelectorAll("div")].filter(
                    (el) => el.textContent && el.children.length && el.getBoundingClientRect
                );
                const el = panels.find(
                    (n) =>
                        n.getBoundingClientRect().width > 150 &&
                        n.getBoundingClientRect().width < window.innerWidth &&
                        /settings/i.test(n.textContent.slice(0, 200)) &&
                        getComputedStyle(n).position === "fixed"
                );
                if (!el) return null;
                const r = el.getBoundingClientRect();
                return { left: r.left, right: r.right, top: r.top, bottom: r.bottom, vw: innerWidth, vh: innerHeight };
            });
            if (rect) {
                const clipped =
                    rect.left < -1 || rect.top < -1 || rect.right > rect.vw + 1 || rect.bottom > rect.vh + 1;
                expect(clipped, `map settings ${w}px clipped ${JSON.stringify(rect)}`).toBe(false);
            }
        });
    }
});
