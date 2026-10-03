// Heap growth profiler: navigates each route, clicks safe buttons, then
// measures retained JS heap after GC. Replaces the coarse Lighthouse heap
// budget with per-interaction attribution.
//
// Usage: node tests/agentic/heap-profiler.cjs [--routes a,b,c] [--json out.json]
// Requires the e2e stack (scripts/e2e/start-e2e-stack.sh) or a running app.

const { chromium } = require("@playwright/test");

const BASE_URL = process.env.AGENTIC_BASE_URL || "http://127.0.0.1:5173";
const GROWTH_BUDGET_BYTES = parseInt(process.env.AGENTIC_HEAP_BUDGET || "8388608", 10); // 8 MiB
const CLICK_CAP = parseInt(process.env.AGENTIC_HEAP_CLICKS || "6", 10);

const SKIP_BUTTON =
    /delete|remove|wipe|clear|erase|format|flash|uninstall|block|unblock|call|dial|hang\s*up|send|shutdown|restart|reboot|logout|purge|destroy|factory|reset|import|export|upload|download|backup|restore|sign|authorize|approve|grant|execute|panic|save|apply|submit|confirm|accept|agree|allow|deny|\byes\b|\bok\b|connect|disconnect|enable|disable|provision|announce|pair|add|create|\bnew\b|update|install|\bset\b|switch|start|stop|\brun\b/i;

function argValue(name, fallback) {
    const i = process.argv.indexOf(`--${name}`);
    return i >= 0 ? process.argv[i + 1] : fallback;
}

async function sampleHeap(page) {
    try {
        await page.evaluate(() => {
            if (typeof window.gc === "function") {
                window.gc();
            }
        });
        await page.waitForTimeout(300);
        const m = await page.evaluate(() => {
            if (performance.measureUserAgentSpecificMemory) {
                return performance.measureUserAgentSpecificMemory().then((r) => r.bytes);
            }
            return performance.memory ? performance.memory.usedJSHeapSize : null;
        });
        return m;
    } catch {
        return null;
    }
}

async function routePaths(page) {
    return page.evaluate(() => {
        try {
            const router = window.__MCX_ROUTER;
            if (router) {
                return router.getRoutes().map((r) => r.path);
            }
        } catch {
            /* fall through */
        }
        return null;
    });
}

function defaultRoutes() {
    const fs = require("fs");
    const path = require("path");
    const src = fs.readFileSync(
        path.resolve(__dirname, "../../meshchatx/src/frontend/main.js"),
        "utf8",
    );
    const paths = [];
    for (const m of src.matchAll(/path:\s*"([^"]+)"/g)) {
        const p = m[1];
        if (p.includes(":") || p === "/auth") {
            continue;
        }
        paths.push(p);
    }
    return paths;
}

async function main() {
    const onlyRoutes = argValue("routes", null);
    const jsonOut = argValue("json", null);

    const browser = await chromium.launch({
        args: ["--js-flags=--expose-gc --enable-precise-memory-info"],
    });
    const ctx = await browser.newContext({ baseURL: BASE_URL });
    const page = await ctx.newPage();

    // Warm up and let the app settle.
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(2500);

    let routes = onlyRoutes ? onlyRoutes.split(",") : null;
    if (!routes) {
        routes = (await routePaths(page)) || defaultRoutes();
    }
    routes = routes.filter((r) => r && !r.includes(":"));

    const report = [];
    for (const route of routes) {
        await page.goto(`/#${route}`, { waitUntil: "domcontentloaded" });
        await page.waitForTimeout(1200);

        const before = await sampleHeap(page);
        const buttons = await page.locator("button:visible").all();
        let clicks = 0;
        for (const btn of buttons.slice(0, CLICK_CAP * 3)) {
            if (clicks >= CLICK_CAP) {
                break;
            }
            const label = ((await btn.textContent()) || "").trim();
            const aria = (await btn.getAttribute("aria-label")) || "";
            if (SKIP_BUTTON.test(label) || SKIP_BUTTON.test(aria)) {
                continue;
            }
            try {
                await btn.click({ timeout: 1500 });
                clicks += 1;
                await page.waitForTimeout(200);
                await page.keyboard.press("Escape");
            } catch {
                // covered/animating controls are skipped
            }
        }
        const after = await sampleHeap(page);
        const delta = before !== null && after !== null ? after - before : null;
        report.push({ route, clicks, heapBefore: before, heapAfter: after, delta });
        console.log(
            `${route}: clicks=${clicks} heap=${fmt(before)} -> ${fmt(after)} (delta ${fmt(delta)})`,
        );
    }

    const over = report.filter((r) => r.delta !== null && r.delta > GROWTH_BUDGET_BYTES);
    if (jsonOut) {
        require("fs").writeFileSync(
            jsonOut,
            JSON.stringify({ generatedAt: new Date().toISOString(), report }, null, 2),
        );
    }
    console.log(`\nheap budget ${fmt(GROWTH_BUDGET_BYTES)} per route`);
    for (const r of over) {
        console.log(`OVER ${r.route}: retained growth ${fmt(r.delta)} after ${r.clicks} clicks`);
    }
    await browser.close();
    process.exit(over.length ? 1 : 0);
}

function fmt(n) {
    if (n === null || n === undefined) {
        return "n/a";
    }
    return `${(n / 1048576).toFixed(1)}MiB`;
}

main().catch((e) => {
    console.error(e);
    process.exit(2);
});
