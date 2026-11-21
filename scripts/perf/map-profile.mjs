#!/usr/bin/env node
// Basemap renderer profiler. Boots the e2e stack (or reuses a running one),
// serves a dense synthetic PMTiles archive through Playwright route
// interception, throttles the CPU 4x via CDP, and measures main-thread
// long tasks and rAF frame deltas for pan, zoomIn, zoomOut and repan in
// each basemap renderer mode (cpu, gpu, raster).
//
// Usage: node scripts/perf/map-profile.mjs [--modes cpu,gpu,raster] [--out /tmp/map-perf2.md]
import { createRequire } from "node:module";
import { spawn } from "node:child_process";
import { writeFileSync } from "node:fs";
import { chromium } from "@playwright/test";

const require = createRequire(import.meta.url);
const { buildDenseArchive } = require("./dense-mvt-fixture.cjs");
const { prepareE2eSession, dismissMapOnboardingTooltip } = require("../../tests/e2e/helpers.js");

const ARCHIVE_HOST = "https://s3.quad4.io/pmtiles/planet.pmtiles";
const OSM_HOST = "https://tile.openstreetmap.org/";
const BASE_URL = `http://${process.env.E2E_VITE_HOST || "127.0.0.1"}:${process.env.E2E_VITE_PORT || "5173"}`;
const THROTTLE = 4;

const args = process.argv.slice(2);
const opt = (name, dflt) => {
    const i = args.indexOf(name);
    return i >= 0 ? args[i + 1] : dflt;
};
const MODES = opt("--modes", "cpu,gpu,raster").split(",");
const OUT = opt("--out", "/tmp/map-perf2.md");
const SETTLE_MS = parseInt(opt("--settle", "3000"), 10);

// 1x1 transparent PNG for raster tile interception.
const PNG_1PX = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
    "base64"
);

async function ensureStack() {
    try {
        const res = await fetch(BASE_URL + "/", { signal: AbortSignal.timeout(3000) });
        if (res.ok) {
            console.log("reusing running stack at " + BASE_URL);
            return null;
        }
    } catch {
        // not running, spawn below
    }
    console.log("starting e2e stack...");
    const child = spawn("bash", ["scripts/e2e/start-e2e-stack.sh"], {
        env: { ...process.env, E2E_LIVE_MESH: "0", E2E_LIVE_MESH2: "0" },
        stdio: ["ignore", "pipe", "pipe"],
    });
    child.stdout.on("data", (d) => process.stdout.write("[stack] " + d));
    child.stderr.on("data", (d) => process.stderr.write("[stack!] " + d));
    const deadline = Date.now() + 300000;
    while (Date.now() < deadline) {
        try {
            const res = await fetch(BASE_URL + "/", { signal: AbortSignal.timeout(3000) });
            if (res.ok) {
                console.log("stack ready");
                return child;
            }
        } catch {
            // keep waiting
        }
        await new Promise((r) => setTimeout(r, 2000));
    }
    child.kill();
    throw new Error("stack did not come up within 300s");
}

const PERF_INIT = `
window.__perf = { frames: [], longtasks: [], marks: [] };
try {
    const po = new PerformanceObserver((list) => {
        for (const e of list.getEntries()) {
            window.__perf.longtasks.push({ start: e.startTime, dur: e.duration });
        }
    });
    po.observe({ type: "longtask", buffered: true });
} catch (e) { /* longtask unsupported */ }
(function loop(last) {
    requestAnimationFrame((t) => {
        window.__perf.frames.push({ t, dt: t - last });
        loop(t);
    });
})(performance.now());
`;

async function runMode(mode, archive, rangeLog) {
    const gpuArgs = ["--enable-unsafe-swiftshader", "--use-angle=swiftshader", "--use-gl=angle"];
    const browser = await chromium.launch({
        headless: true,
        args: mode === "gpu" ? gpuArgs : [],
    });
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    await context.addInitScript((m) => {
        localStorage.setItem("mcx.map-basemap-renderer", m);
        localStorage.setItem("meshchatx.map.offlineMode", "0");
        localStorage.setItem("map_onboarding_seen", "true");
    }, mode);
    await context.addInitScript(PERF_INIT);
    const page = await context.newPage();

    await page.route(`${ARCHIVE_HOST}**`, async (route) => {
        const range = route.request().headers()["range"] || "";
        rangeLog.push(Date.now());
        const m = /bytes=(\d+)-(\d+)/.exec(range);
        if (!m) {
            return route.fulfill({
                status: 200,
                body: archive,
                headers: { "access-control-allow-origin": "*" },
            });
        }
        const start = parseInt(m[1], 10);
        const end = Math.min(parseInt(m[2], 10), archive.length - 1);
        return route.fulfill({
            status: 206,
            body: archive.subarray(start, end + 1),
            headers: {
                "content-range": `bytes ${start}-${end}/${archive.length}`,
                "content-length": String(end - start + 1),
                "accept-ranges": "bytes",
                "access-control-allow-origin": "*",
                "last-modified": "Thu, 20 Nov 2025 00:00:00 GMT",
                etag: '"synthetic-dense-v1"',
            },
        });
    });
    // Sprite metadata must be valid JSON or ol-mapbox-style fails the whole
    // style and the CPU path silently falls back to raster. Glyphs get empty
    // bytes: missing glyph stacks skip labels but do not break the render.
    await page.route("https://protomaps.github.io/**", (route) => {
        const url = route.request().url();
        if (url.endsWith(".json")) {
            return route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
        }
        if (url.endsWith(".png")) {
            return route.fulfill({ status: 200, body: PNG_1PX, contentType: "image/png" });
        }
        return route.fulfill({ status: 200, body: Buffer.alloc(0) });
    });
    await page.route(`${OSM_HOST}**`, (route) => {
        rangeLog.push(Date.now());
        return route.fulfill({ status: 200, body: PNG_1PX, contentType: "image/png" });
    });

    const warnings = [];
    page.on("console", (msg) => {
        if (msg.type() === "warning" || msg.type() === "error") warnings.push(msg.text().slice(0, 200));
    });

    const client = await context.newCDPSession(page);
    await client.send("Emulation.setCPUThrottlingRate", { rate: THROTTLE });

    await prepareE2eSession(page.request);
    await page.goto(BASE_URL + "/#/map");
    await dismissMapOnboardingTooltip(page);
    await page.waitForSelector(".ol-viewport canvas, .mcx-maplibre-basemap canvas", { timeout: 90000 });
    await page.waitForTimeout(4000);
    // Center on lon/lat 0,0: the dense fixture covers z5-z8 in a window
    // around the origin. [0,0] is the same point in EPSG:3857.
    await page.evaluate(() => {
        const view = window.__mcxMap && window.__mcxMap.getView();
        if (view) {
            view.setCenter([0, 0]);
            view.setZoom(4);
        }
    });
    await page.waitForTimeout(2500);

    const rendererInfo = await page.evaluate(() => {
        const maplibre = document.querySelector(".mcx-maplibre-basemap canvas");
        let glRenderer = "none";
        if (maplibre) {
            const gl = maplibre.getContext("webgl2") || maplibre.getContext("webgl");
            if (gl) {
                const ext = gl.getExtension("WEBGL_debug_renderer_info");
                glRenderer = ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
            }
        }
        return { maplibre: !!maplibre, glRenderer };
    });

    const box = await page.locator(".ol-viewport").boundingBox();
    const cx = box.x + box.width / 2;
    const cy = box.y + box.height / 2;

    async function measure(name, gesture) {
        await page.evaluate(() => {
            window.__perf.frames.length = 0;
            window.__perf.longtasks.length = 0;
            window.__perf.t0 = performance.now();
        });
        const reqStart = rangeLog.length;
        await gesture();
        await page.waitForTimeout(SETTLE_MS);
        const m = await page.evaluate(() => ({
            t0: window.__perf.t0,
            t1: performance.now(),
            frames: window.__perf.frames.slice(),
            lts: window.__perf.longtasks.slice(),
        }));
        const inWindow = (e) => e.start >= m.t0 && e.start <= m.t1;
        const lts = m.lts.filter(inWindow);
        const frames = m.frames.filter((f) => f.t >= m.t0 && f.t <= m.t1).map((f) => f.dt);
        frames.sort((a, b) => a - b);
        const p = (q) => (frames.length ? frames[Math.min(frames.length - 1, Math.floor(frames.length * q))] : 0);
        return {
            name,
            longtaskTotal: Math.round(lts.reduce((a, e) => a + e.dur, 0)),
            longtaskCount: lts.length,
            maxLongtask: Math.round(lts.reduce((a, e) => Math.max(a, e.dur), 0)),
            maxFrame: Math.round(frames.length ? frames[frames.length - 1] : 0),
            p95Frame: Math.round(p(0.95)),
            meanFrame: Math.round(frames.reduce((a, b) => a + b, 0) / Math.max(1, frames.length)),
            frameCount: frames.length,
            requests: rangeLog.length - reqStart,
        };
    }

    const results = [];
    results.push(
        await measure("pan", async () => {
            await page.mouse.move(cx, cy);
            await page.mouse.down();
            for (let i = 1; i <= 8; i++) {
                await page.mouse.move(cx + i * 40, cy + i * 10, { steps: 2 });
            }
            await page.mouse.up();
        })
    );
    results.push(
        await measure("zoomIn", async () => {
            await page.mouse.move(cx, cy);
            for (let i = 0; i < 3; i++) {
                await page.mouse.wheel(0, -300);
                await page.waitForTimeout(350);
            }
        })
    );
    results.push(
        await measure("zoomOut", async () => {
            await page.mouse.move(cx, cy);
            for (let i = 0; i < 3; i++) {
                await page.mouse.wheel(0, 300);
                await page.waitForTimeout(350);
            }
        })
    );
    results.push(
        await measure("repan", async () => {
            await page.mouse.move(cx, cy);
            await page.mouse.down();
            for (let i = 1; i <= 8; i++) {
                await page.mouse.move(cx - i * 40, cy - i * 10, { steps: 2 });
            }
            await page.mouse.up();
        })
    );

    await browser.close();
    return { mode, rendererInfo, results, warnings: warnings.slice(0, 10) };
}

async function main() {
    const stack = await ensureStack();
    try {
        console.log("building dense archive...");
        const archive = buildDenseArchive();
        console.log(`archive ${(archive.length / 1e6).toFixed(1)}MB`);

        const rangeLog = [];
        const all = [];
        for (const mode of MODES) {
            console.log(`--- mode ${mode} ---`);
            all.push(await runMode(mode, archive, rangeLog));
        }

        const lines = [];
        lines.push("# Map perf round 2");
        lines.push("");
        lines.push(`Chromium headless, CDP CPU throttle ${THROTTLE}x, settle ${SETTLE_MS}ms.`);
        lines.push(`Dense synthetic PMTiles fixture (~${(archive.length / 1e6).toFixed(1)}MB, ~300 features/tile, layers matching the Protomaps style). Archive and OSM raster served via Playwright route interception, so no real network.`);
        lines.push("");
        for (const r of all) {
            lines.push(`## ${r.mode} (maplibre canvas: ${r.rendererInfo.maplibre}, gl: ${r.rendererInfo.glRenderer})`);
            lines.push("");
            lines.push("| gesture | longtask total ms | longtask count | max longtask ms | max frame ms | p95 frame ms | mean frame ms | frames | range reqs |");
            lines.push("|---|---|---|---|---|---|---|---|---|");
            for (const g of r.results) {
                lines.push(
                    `| ${g.name} | ${g.longtaskTotal} | ${g.longtaskCount} | ${g.maxLongtask} | ${g.maxFrame} | ${g.p95Frame} | ${g.meanFrame} | ${g.frameCount} | ${g.requests} |`
                );
            }
            lines.push("");
            if (r.warnings.length) {
                lines.push("console warnings: " + r.warnings.join(" | "));
                lines.push("");
            }
        }
        writeFileSync(OUT, lines.join("\n"));
        console.log("wrote " + OUT);
        console.log(JSON.stringify(all.map((r) => ({ mode: r.mode, gl: r.rendererInfo.glRenderer, results: r.results })), null, 1));
    } finally {
        if (stack) {
            stack.kill("SIGTERM");
        }
    }
}

main().catch((e) => {
    console.error(e);
    process.exit(1);
});
