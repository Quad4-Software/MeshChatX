// SPDX-License-Identifier: 0BSD
//
// Observed-vitals guard for UI pages under simulated data. Unlike the
// Lighthouse audit (Lantern-simulated scores), this measures real numbers on
// the runner: cold-load FCP/LCP with the HTTP cache disabled, SPA hash-route
// transition latency, an API round-trip, and post-mount JS heap.
//
//   MESHCHAT_UI_PROD=1 pnpm exec playwright test \
//     --config playwright.ui.config.js tests/ui/perf.spec.js
//
// Budgets live in tests/ui/pages.js (DEFAULT_PERF_BUDGETS + per-page perf).
// Results are written to test-results/perf/<page>.json for CI artifacts.

const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");
const { dismissMapOnboardingTooltip } = require("../e2e/helpers");
const { resolvePages, perfBudgetsFor } = require("./pages");
const { seedUiSimulatedData } = require("./seed");
const { waitForBootReady, waitForPageReady, gotoUiPage } = require("./ready");

const NEUTRAL = { id: "about", path: "/about", ready: "Active sessions" };
const REPORT_DIR = path.join(__dirname, "..", "..", "test-results", "perf");

// Buffered LCP entries are observer-only. Record the latest paint timestamp.
const LCP_INIT = `
window.__perfLcp = 0;
try {
    new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
            window.__perfLcp = entry.startTime;
        }
    }).observe({ type: "largest-contentful-paint", buffered: true });
} catch (e) { /* observer unsupported */ }
`;

const pages = resolvePages({
    ciOnly: process.env.MESHCHAT_UI_CI === "1",
    ids: process.env.MESHCHAT_UI_PAGES
        ? process.env.MESHCHAT_UI_PAGES.split(",")
              .map((s) => s.trim())
              .filter(Boolean)
        : null,
});

async function coldLoadMetrics(page, cdp) {
    const timing = await page.evaluate(() => {
        const nav = performance.getEntriesByType("navigation")[0] || {};
        const fcp =
            (performance.getEntriesByType("paint") || []).find((p) => p.name === "first-contentful-paint")?.startTime ||
            0;
        return {
            fcpMs: Math.round(fcp),
            lcpMs: Math.round(window.__perfLcp || 0),
            domContentLoadedMs: Math.round(nav.domContentLoadedEventEnd || 0),
            loadMs: Math.round(nav.loadEventEnd || 0),
        };
    });
    const { metrics } = await cdp.send("Performance.getMetrics");
    timing.heapMb = Math.round(((metrics.find((m) => m.name === "JSHeapUsedSize")?.value || 0) / 1048576) * 10) / 10;
    return timing;
}

async function apiRoundTripMs(page) {
    return page.evaluate(async () => {
        const t0 = performance.now();
        try {
            await fetch("/api/v1/status", { cache: "no-store" });
        } catch (e) {
            /* measured anyway */
        }
        return Math.round(performance.now() - t0);
    });
}

test.describe("per-page observed vitals", () => {
    test.describe.configure({ mode: "serial", timeout: 180000 });

    test.beforeAll(async ({ request }) => {
        await seedUiSimulatedData(request);
    });

    for (const entry of pages) {
        test(`perf: ${entry.id}`, async ({ browser, baseURL }) => {
            // Fresh context + disabled HTTP cache = true cold load per page.
            const context = await browser.newContext();
            const page = await context.newPage();
            const cdp = await context.newCDPSession(page);
            try {
                await cdp.send("Network.enable");
                await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
                await cdp.send("Performance.enable");
                await page.addInitScript(LCP_INIT);

                const url = `${baseURL.replace(/\/$/, "")}/#${entry.path}`;
                await page.goto(url, { waitUntil: "domcontentloaded" });
                await waitForBootReady(page);
                await waitForPageReady(page, entry);
                if (entry.id === "map") {
                    await dismissMapOnboardingTooltip(page);
                }
                // LCP can keep updating while larger content settles.
                await page.waitForTimeout(400);

                const metrics = await coldLoadMetrics(page, cdp);
                metrics.apiMs = await apiRoundTripMs(page);

                // SPA transition latency: leave to a neutral page, then time
                // the hash-route change back until the ready signal paints.
                await gotoUiPage(page, NEUTRAL, baseURL);
                const navStart = Date.now();
                await page.evaluate((p) => {
                    window.location.hash = p;
                }, entry.path);
                await waitForPageReady(page, entry);
                metrics.navMs = Date.now() - navStart;

                const budgets = perfBudgetsFor(entry);
                metrics.budgets = budgets;
                fs.mkdirSync(REPORT_DIR, { recursive: true });
                fs.writeFileSync(path.join(REPORT_DIR, `${entry.id}.json`), JSON.stringify(metrics, null, 2));

                // eslint-disable-next-line no-console
                console.log(
                    `perf ${entry.id}: fcp=${metrics.fcpMs}ms lcp=${metrics.lcpMs}ms ` +
                        `dcl=${metrics.domContentLoadedMs}ms load=${metrics.loadMs}ms ` +
                        `nav=${metrics.navMs}ms api=${metrics.apiMs}ms heap=${metrics.heapMb}MB`
                );

                const failures = [];
                for (const key of ["fcpMs", "lcpMs", "domContentLoadedMs", "loadMs", "navMs", "heapMb"]) {
                    const actual = metrics[key];
                    const budget = budgets[key];
                    if (budget != null && actual > budget) {
                        failures.push(`${key} ${actual} > ${budget}`);
                    }
                }
                expect(failures, `${entry.id} exceeded perf budgets`).toEqual([]);
            } finally {
                await context.close();
            }
        });
    }
});
