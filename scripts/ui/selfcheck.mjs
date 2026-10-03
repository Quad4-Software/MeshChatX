#!/usr/bin/env node
// SPDX-License-Identifier: 0BSD

/**
 * Fast UI selfcheck. Crawls every app route, opens nav menus and dropdowns,
 * and reports pageerrors + console errors + failed requests per route.
 *
 * Usage:
 *   node scripts/ui/selfcheck.mjs                       # default http://127.0.0.1:5173
 *   node scripts/ui/selfcheck.mjs --url http://x:5173
 *   node scripts/ui/selfcheck.mjs --backend http://127.0.0.1:8000  # CSRF origin
 *   node scripts/ui/selfcheck.mjs --slow               # 1.5s settle per route
 *   node scripts/ui/selfcheck.mjs --headed             # show the browser
 *   node scripts/ui/selfcheck.mjs --json               # machine-readable report
 *   node scripts/ui/selfcheck.mjs --routes /map,/tools # subset
 */

import { chromium } from "playwright";

const args = process.argv.slice(2);
function argValue(flag, fallback) {
    const i = args.indexOf(flag);
    return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
}
const BASE = argValue("--url", "http://127.0.0.1:5173").replace(/\/$/, "");
const BACKEND = argValue("--backend", "https://127.0.0.1:8000").replace(/\/$/, "");
const SLOW = args.includes("--slow");
const HEADED = args.includes("--headed");
const JSON_OUT = args.includes("--json");
const ROUTE_FILTER = argValue("--routes", "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
const SETTLE_MS = SLOW ? 1500 : 550;

const ROUTES = [
    "/",
    "/about",
    "/interfaces",
    "/interfaces/add",
    "/messages",
    "/contacts",
    "/map",
    "/network-visualiser",
    "/nomadnetwork",
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

// Error text patterns that are noise, not bugs.
const IGNORED_CONSOLE = [
    /net::ERR_/i,
    /failed to fetch/i,
    /websocket/i,
    /404/,
    /SRI hash mismatch/i, // local rebuilds change hashes; integrity.json is regenerated
    /favicon/i,
    /deprecation/i,
    /ResizeObserver/i,
    /Download the React DevTools/i,
    /hydration/i,
    /content script/i,
    /AbortError/i,
    /signal is aborted/i,
];

async function prepareSession(context) {
    // Dismiss tutorial + changelog gates so routes render directly.
    try {
        const csrfRes = await context.request.get(`${BACKEND}/api/v1/auth/csrf`, {
            ignoreHTTPSErrors: true,
        });
        if (!csrfRes.ok()) return;
        const { csrf_token } = await csrfRes.json();
        const headers = { "X-CSRF-Token": csrf_token };
        await context.request.post(`${BACKEND}/api/v1/app/tutorial/seen`, {
            headers,
            ignoreHTTPSErrors: true,
        });
        await context.request.post(`${BACKEND}/api/v1/app/changelog/seen`, {
            headers,
            ignoreHTTPSErrors: true,
            data: { version: "999.999.999" },
        });
    } catch {
        // Backend without auth/session endpoints; still crawl.
    }
}

function isNoise(text) {
    return IGNORED_CONSOLE.some((re) => re.test(text));
}

async function crawlRoute(page, route, report) {
    const errors = [];
    const pageErr = (e) => errors.push(`pageerror: ${e.message}`);
    const consoleErr = (msg) => {
        if (msg.type() === "error" && !isNoise(msg.text())) {
            errors.push(`console: ${msg.text()}`);
        }
    };
    const reqErr = (req) => {
        if (req.failure() && !isNoise(req.failure().errorText)) {
            errors.push(`requestfailed: ${req.url()} (${req.failure().errorText})`);
        }
    };
    const respErr = (resp) => {
        if (resp.status() >= 500 && !isNoise(resp.url())) {
            errors.push(`http ${resp.status()}: ${resp.url()}`);
        }
    };
    page.on("pageerror", pageErr);
    page.on("console", consoleErr);
    page.on("requestfailed", reqErr);
    page.on("response", respErr);

    try {
        await page.goto(`${BASE}/#${route}`, { waitUntil: "domcontentloaded", timeout: 20000 });
        await page.waitForTimeout(SETTLE_MS);
        const text = await page
            .locator("body")
            .innerText()
            .catch(() => "");
        const empty = text.trim().length === 0;
        report.push({
            route,
            ok: errors.length === 0 && !empty,
            empty,
            errors: [...new Set(errors)],
        });
    } catch (e) {
        report.push({ route, ok: false, empty: false, errors: [`navigation: ${e.message}`] });
    } finally {
        page.off("pageerror", pageErr);
        page.off("console", consoleErr);
        page.off("requestfailed", reqErr);
        page.off("response", respErr);
    }
}

async function probeMenus(page, report) {
    // Open each top-nav menu and the "More"/sidebar flyouts, catch errors.
    const menuErrors = [];
    const pageErr = (e) => menuErrors.push(`pageerror: ${e.message}`);
    const consoleErr = (msg) => {
        if (msg.type() === "error" && !isNoise(msg.text())) {
            menuErrors.push(`console: ${msg.text()}`);
        }
    };
    page.on("pageerror", pageErr);
    page.on("console", consoleErr);
    try {
        await page.goto(`${BASE}/#/messages`, { waitUntil: "domcontentloaded" });
        await page.waitForTimeout(SETTLE_MS);
        const clickables = await page
            .locator("button[aria-haspopup], [role='button'][aria-haspopup], button[aria-expanded]")
            .all();
        for (const btn of clickables) {
            try {
                const label = (await btn.getAttribute("aria-label")) || (await btn.innerText()) || "?";
                menuErrors.length = 0;
                await btn.click({ timeout: 2500 });
                await page.waitForTimeout(300);
                // Close via Escape or click-away.
                await page.keyboard.press("Escape");
                await page.waitForTimeout(150);
                if (menuErrors.length) {
                    report.push({
                        route: `menu:${label.slice(0, 40)}`,
                        ok: false,
                        empty: false,
                        errors: [...new Set(menuErrors)],
                    });
                }
            } catch {
                // Non-interactive or hidden control; skip.
            }
        }
    } finally {
        page.off("pageerror", pageErr);
        page.off("console", consoleErr);
    }
}

async function probeSettings(page, report) {
    // Walk each settings sidebar section and expand its content.
    const errors = [];
    const pageErr = (e) => errors.push(`pageerror: ${e.message}`);
    const consoleErr = (msg) => {
        if (msg.type() === "error" && !isNoise(msg.text())) {
            errors.push(`console: ${msg.text()}`);
        }
    };
    page.on("pageerror", pageErr);
    page.on("console", consoleErr);
    try {
        await page.goto(`${BASE}/#/settings`, { waitUntil: "domcontentloaded" });
        await page.waitForTimeout(SETTLE_MS);
        const items = await page.locator("aside a[href*='#'], nav a[href*='#'], .setting-section-nav a").all();
        const seen = new Set();
        for (const item of items.slice(0, 30)) {
            try {
                const href = await item.getAttribute("href");
                if (!href || seen.has(href)) continue;
                seen.add(href);
                errors.length = 0;
                await item.click({ timeout: 2500 });
                await page.waitForTimeout(300);
                if (errors.length) {
                    report.push({
                        route: `settings:${href}`,
                        ok: false,
                        empty: false,
                        errors: [...new Set(errors)],
                    });
                }
            } catch {
                // skip
            }
        }
    } finally {
        page.off("pageerror", pageErr);
        page.off("console", consoleErr);
    }
}

async function main() {
    const routes = ROUTE_FILTER.length ? ROUTE_FILTER : ROUTES;
    const browser = await chromium.launch({ headless: !HEADED, ignoreHTTPSErrors: true });
    const context = await browser.newContext({
        viewport: { width: 1360, height: 900 },
        ignoreHTTPSErrors: true,
    });
    await prepareSession(context);
    const page = await context.newPage();

    const report = [];
    const t0 = Date.now();
    for (const route of routes) {
        await crawlRoute(page, route, report);
        const last = report[report.length - 1];
        if (!JSON_OUT) {
            const mark = last.ok ? "ok  " : "FAIL";
            console.log(`${mark} ${route}${last.empty ? " (empty body)" : ""}`);
            for (const e of last.errors) console.log(`      ${e}`);
        }
    }
    await probeMenus(page, report);
    await probeSettings(page, report);

    const fails = report.filter((r) => !r.ok);
    if (JSON_OUT) {
        console.log(
            JSON.stringify(
                {
                    durationMs: Date.now() - t0,
                    routes: report.length,
                    failed: fails.length,
                    report,
                },
                null,
                2
            )
        );
    } else {
        console.log(`\n${report.length} checks, ${fails.length} failed, ${((Date.now() - t0) / 1000).toFixed(1)}s`);
        if (fails.length) {
            console.log("\nFailures:");
            for (const f of fails) {
                console.log(`  ${f.route}`);
                for (const e of f.errors) console.log(`    ${e}`);
            }
        }
    }
    await browser.close();
    process.exit(fails.length ? 1 : 0);
}

main().catch((e) => {
    console.error("selfcheck crashed:", e);
    process.exit(2);
});
