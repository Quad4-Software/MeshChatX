// SPDX-License-Identifier: 0BSD
//
// Heap and listener growth profiler for UI pages under simulated data.
// Run with the UI stack config:
//   MESHCHAT_UI_PROD=1 pnpm exec playwright test \
//     --config playwright.ui.config.js tests/ui/heap-profile.spec.js
//
// Instruments addEventListener/removeEventListener and the timer APIs before
// page scripts run, then mounts and unmounts each catalog page several times,
// forcing GC through CDP between cycles. Per page it reports listener and
// timer deltas plus used JS heap before/after so growth shows up as a
// non-zero trend across cycles.

const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");
const { dismissMapOnboardingTooltip } = require("../e2e/helpers");
const { resolvePages } = require("./pages");
const { seedUiSimulatedData } = require("./seed");
const { gotoUiPage } = require("./ready");

const CYCLES = Number(process.env.MESHCHAT_HEAP_CYCLES || 5);
const NEUTRAL_PATH = "/about";
const REPORT_DIR = path.join(__dirname, "..", "..", "test-results", "heap");

// Per-page growth budgets measured after CYCLES mount/unmount rounds with a
// forced GC between each. Values are generous: the goal is catching leaks and
// unbounded re-registration, not pinning exact counts on noisy CI runners.
const HEAP_BUDGETS = {
    heapDeltaMb: Number(process.env.MESHCHAT_HEAP_MAX_DELTA_MB || 30),
    nodes: Number(process.env.MESHCHAT_HEAP_MAX_NODES || 500),
    listeners: Number(process.env.MESHCHAT_HEAP_MAX_LISTENERS || 10),
    timeouts: Number(process.env.MESHCHAT_HEAP_MAX_TIMEOUTS || 10),
    intervals: Number(process.env.MESHCHAT_HEAP_MAX_INTERVALS || 3),
    rafs: Number(process.env.MESHCHAT_HEAP_MAX_RAFS || 3),
};

const INSTRUMENT = `
(() => {
    const c = { listeners: 0, timeouts: 0, intervals: 0, rafs: 0 };
    const add = EventTarget.prototype.addEventListener;
    const del = EventTarget.prototype.removeEventListener;
    EventTarget.prototype.addEventListener = function (...a) {
        c.listeners++;
        return add.apply(this, a);
    };
    EventTarget.prototype.removeEventListener = function (...a) {
        c.listeners--;
        return del.apply(this, a);
    };
    const st = window.setTimeout;
    const ct = window.clearTimeout;
    window.setTimeout = function (fn, delay, ...rest) {
        c.timeouts++;
        const wrapped =
            typeof fn === "function"
                ? (...args) => {
                      c.timeouts--;
                      return fn(...args);
                  }
                : fn;
        return st.call(this, wrapped, delay, ...rest);
    };
    window.clearTimeout = function (id) {
        if (id !== undefined) c.timeouts--;
        return ct.call(this, id);
    };
    const si = window.setInterval;
    const ci = window.clearInterval;
    window.setInterval = function (...a) {
        c.intervals++;
        return si.apply(this, a);
    };
    window.clearInterval = function (id) {
        if (id !== undefined) c.intervals--;
        return ci.call(this, id);
    };
    const raf = window.requestAnimationFrame;
    const caf = window.cancelAnimationFrame;
    window.requestAnimationFrame = function (fn) {
        c.rafs++;
        return raf.call(this, (t) => {
            c.rafs--;
            return fn(t);
        });
    };
    window.cancelAnimationFrame = function (id) {
        c.rafs--;
        return caf.call(this, id);
    };
    window.__leakCounters = c;
    // rAF callbacks that re-register keep the count steady, so the delta
    // after unmount is what matters, not the instantaneous value.
})();
`;

async function measure(page, cdp) {
    await cdp.send("HeapProfiler.collectGarbage");
    const { metrics } = await cdp.send("Performance.getMetrics");
    const pick = (name) => metrics.find((m) => m.name === name)?.value || 0;
    const counters = await page.evaluate(() => window.__leakCounters);
    return {
        heap: pick("JSHeapUsedSize"),
        nodes: pick("Nodes"),
        listeners: pick("JSEventListeners"),
        timeouts: counters.timeouts,
        intervals: counters.intervals,
        rafs: counters.rafs,
    };
}

function fmt(bytes) {
    return (bytes / 1024 / 1024).toFixed(2) + " MB";
}

test.describe("heap profile across pages", () => {
    test.beforeAll(async ({ request }) => {
        await seedUiSimulatedData(request);
    });

    test("per-page listener and heap deltas", async ({ page, baseURL }) => {
        test.setTimeout(600000);
        await page.addInitScript(INSTRUMENT);
        const cdp = await page.context().newCDPSession(page);
        await cdp.send("HeapProfiler.enable");
        await cdp.send("Performance.enable");

        const neutral = { id: "about", path: NEUTRAL_PATH, ready: "Active sessions" };
        const pages = resolvePages({
            ciOnly: process.env.MESHCHAT_UI_CI === "1",
            ids: process.env.MESHCHAT_UI_PAGES
                ? process.env.MESHCHAT_UI_PAGES.split(",")
                      .map((s) => s.trim())
                      .filter(Boolean)
                : null,
        }).filter((p) => p.path !== NEUTRAL_PATH);

        // Warm the app shell once so module-level caches reach steady state.
        await gotoUiPage(page, neutral, baseURL);
        await measure(page, cdp);

        const report = [];
        for (const entry of pages) {
            try {
                // One warm cycle absorbs first-mount module and cache costs so
                // the measured delta shows only per-mount growth.
                await gotoUiPage(page, entry, baseURL);
                if (entry.id === "map") {
                    await dismissMapOnboardingTooltip(page);
                }
            } catch (e) {
                report.push({ page: entry.id, skipped: String(e).slice(0, 80) });
                continue;
            }
            await gotoUiPage(page, neutral, baseURL);
            const before = await measure(page, cdp);
            let after = before;
            for (let i = 0; i < CYCLES; i++) {
                await gotoUiPage(page, entry, baseURL);
                await gotoUiPage(page, neutral, baseURL);
                after = await measure(page, cdp);
            }
            report.push({
                page: entry.id,
                heapDelta: after.heap - before.heap,
                nodes: after.nodes - before.nodes,
                listeners: after.listeners - before.listeners,
                timeouts: after.timeouts - before.timeouts,
                intervals: after.intervals - before.intervals,
                rafs: after.rafs - before.rafs,
            });
        }

        fs.mkdirSync(REPORT_DIR, { recursive: true });
        const failures = [];
        for (const row of report) {
            if (row.skipped) {
                console.log(`heap-profile | ${row.page.padEnd(24)} SKIPPED ${row.skipped}`);
                continue;
            }
            console.log(
                `heap-profile | ${row.page.padEnd(24)} heap ${fmt(row.heapDelta).padStart(9)} ` +
                    `nodes ${String(row.nodes).padStart(6)} ` +
                    `listeners ${String(row.listeners).padStart(4)} ` +
                    `timeouts ${String(row.timeouts).padStart(4)} ` +
                    `intervals ${String(row.intervals).padStart(3)} ` +
                    `rafs ${String(row.rafs).padStart(4)}`
            );
            fs.writeFileSync(
                path.join(REPORT_DIR, `${row.page}.json`),
                JSON.stringify({ budgets: HEAP_BUDGETS, ...row }, null, 2)
            );
            const checks = [
                ["heapDelta", row.heapDelta, HEAP_BUDGETS.heapDeltaMb * 1048576],
                ["nodes", row.nodes, HEAP_BUDGETS.nodes],
                ["listeners", row.listeners, HEAP_BUDGETS.listeners],
                ["timeouts", row.timeouts, HEAP_BUDGETS.timeouts],
                ["intervals", row.intervals, HEAP_BUDGETS.intervals],
                ["rafs", row.rafs, HEAP_BUDGETS.rafs],
            ];
            for (const [name, actual, budget] of checks) {
                if (actual > budget) {
                    failures.push(`${row.page}: ${name} ${actual} > ${budget}`);
                }
            }
        }
        expect(failures, "pages exceeded heap growth budgets").toEqual([]);
    });
});
