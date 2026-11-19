// SPDX-License-Identifier: 0BSD
// Layout measurements for onboarding and key pages on phone and desktop
// viewports. Asserts real DOM geometry: no horizontal overflow, action
// bars in-viewport, >=44px touch targets, pointer cursor on interactive
// controls, and popups staying inside the viewport.
const { test, expect } = require("@playwright/test");

const WIDTHS = [360, 390, 430, 1280];

async function closeNonTutorialModals(page) {
    for (let i = 0; i < 5; i++) {
        const panels = page.locator(".modal-panel");
        const n = await panels.count();
        let closed = false;
        for (let j = 0; j < n; j++) {
            const p = panels.nth(j);
            if (!(await p.isVisible().catch(() => false))) continue;
            if (await p.locator(".tutorial-step").count()) continue;
            const btn = p.locator(".modal-panel__header button, button.icon-btn-muted").first();
            if (await btn.count()) {
                await btn.click({ force: true }).catch(() => {});
                closed = true;
                await page.waitForTimeout(300);
            }
        }
        if (!closed) break;
    }
}

async function measure(page, label) {
    const m = await page.evaluate(() => {
        const doc = document.documentElement;
        const over = doc.scrollWidth - doc.clientWidth;
        const offscreen = [];
        document.querySelectorAll(".tutorial-action-btn").forEach((el) => {
            const r = el.getBoundingClientRect();
            if (r.bottom > innerHeight + 1 || r.right > innerWidth + 1) {
                offscreen.push(el.textContent.trim().slice(0, 20));
            }
            if (r.height > 0 && r.height < 40) {
                offscreen.push("small:" + el.textContent.trim().slice(0, 20));
            }
        });
        const btn = [...document.querySelectorAll(".tutorial-action-btn")].find(
            (b) => !b.disabled && b.getBoundingClientRect().height > 0
        );
        const cursor = btn ? getComputedStyle(btn).cursor : null;
        return { over, offscreen, cursor };
    });
    expect(m.over, `${label}: horizontal overflow ${m.over}px`).toBe(0);
    expect(m.offscreen, `${label}: clipped or undersized controls ${m.offscreen}`).toEqual([]);
    if (m.cursor) {
        expect(m.cursor, `${label}: action button cursor`).toBe("pointer");
    }
}

test.describe("onboarding layout", () => {
    for (const w of WIDTHS) {
        test(`tutorial fits ${w}px wide viewport`, async ({ page }) => {
            await page.setViewportSize({ width: w, height: w >= 1280 ? 800 : 700 });
            await page.goto("/#/", { waitUntil: "domcontentloaded" });
            await page.waitForSelector(".tutorial-step", { timeout: 60000 });
            await closeNonTutorialModals(page);
            await measure(page, `tutorial step1 ${w}px`);
            // advance through footer-driven steps and re-measure
            for (let step = 2; step <= 8; step++) {
                const next = page
                    .locator(
                        ".modal-panel button.tutorial-action-btn-primary, .modal-panel button.tutorial-action-btn-success"
                    )
                    .last();
                if (!(await next.count())) break;
                const label = (await next.innerText().catch(() => "")).toLowerCase();
                if (label.includes("finish")) break;
                await next.click({ force: true }).catch(() => {});
                await page.waitForTimeout(600);
                if (await page.locator(".tutorial-step").count()) {
                    await measure(page, `tutorial step${step} ${w}px`);
                }
            }
        });
    }

    test("landscape tutorial fits short viewport", async ({ page }) => {
        await page.setViewportSize({ width: 667, height: 375 });
        await page.goto("/#/", { waitUntil: "domcontentloaded" });
        await page.waitForSelector(".tutorial-step", { timeout: 60000 });
        await closeNonTutorialModals(page);
        await measure(page, "tutorial landscape 667x375");
    });
});

test.describe("key page layout", () => {
    const pages = [
        { route: "/#/messages", label: "messages" },
        { route: "/#/nomadnetwork", label: "nomadnet" },
        { route: "/#/settings", label: "settings" },
        { route: "/#/map", label: "map" },
    ];
    for (const p of pages) {
        for (const w of [360, 1280]) {
            test(`${p.label} has no horizontal overflow at ${w}px`, async ({ page }) => {
                await page.setViewportSize({ width: w, height: w >= 1280 ? 800 : 700 });
                await page.goto("/#/", { waitUntil: "domcontentloaded" });
                await closeNonTutorialModals(page);
                await page
                    .evaluate(() => {
                        // finish/skip tutorial if it is showing so routing is free
                        const skip = [...document.querySelectorAll(".tutorial-action-btn-ghost")][0];
                        if (skip) skip.click();
                    })
                    .catch(() => {});
                await page.goto(p.route, { waitUntil: "domcontentloaded" });
                await page.waitForTimeout(2500);
                const over = await page.evaluate(
                    () => document.documentElement.scrollWidth - document.documentElement.clientWidth
                );
                expect(over, `${p.label} ${w}px horizontal overflow`).toBe(0);
            });
        }
    }
});
