const fs = require("fs");
const path = require("path");
const lighthouseModule = require("lighthouse");
const lighthouse = lighthouseModule.default || lighthouseModule;
const desktopConfig = lighthouseModule.desktopConfig;
const puppeteer = require("puppeteer-core");

const LH_DEBUG_PORT = parseInt(process.env.LH_DEBUG_PORT || "9222", 10);
const REPORT_DIR = process.env.LH_REPORT_DIR || path.join("test-results", "lighthouse");

/**
 * Production-page Lighthouse config.
 * Blocks the long-lived /ws socket so network-idle (and LCP/TTI) are not held open forever.
 */
function buildLhConfig(formFactor) {
    const base = desktopConfig || { extends: "lighthouse:default", settings: {} };
    return {
        ...base,
        settings: {
            ...(base.settings || {}),
            onlyCategories: ["performance", "accessibility", "best-practices"],
            formFactor: formFactor || "desktop",
            throttlingMethod: "simulate",
            maxWaitForLoad: 45000,
            networkQuietThresholdMs: 1000,
            pauseAfterFcpMs: 1000,
            pauseAfterLoadMs: 1000,
            blockedUrlPatterns: ["*://*/ws", "*://*/ws?*", "ws://*/*", "wss://*/*", "*service-worker.js*"],
            screenEmulation:
                formFactor === "mobile"
                    ? undefined
                    : {
                          mobile: false,
                          width: 1350,
                          height: 940,
                          deviceScaleFactor: 1,
                          disabled: false,
                      },
        },
    };
}

/**
 * Attach to the Playwright-controlled page over CDP so the audit runs on
 * the prepared target. lighthouse(url) opens its own puppeteer tab, which
 * would bypass the History-API freeze that keeps the app from navigating
 * mid-gather.
 *
 * @param {string} url absolute page URL including hash route
 * @param {number} port CDP port
 * @returns {Promise<{page: LH.Puppeteer.Page, browser: LH.Puppeteer.Browser}|undefined>}
 */
async function findAuditablePage(url, port) {
    let browser;
    try {
        browser = await puppeteer.connect({
            browserURL: `http://127.0.0.1:${port}`,
            defaultViewport: null,
        });
    } catch {
        return undefined;
    }
    const pages = await browser.pages();
    const page = pages.find((p) => p.url() === url) ||
        pages.find((p) => p.url().startsWith(new URL(url).origin));
    if (!page) {
        await browser.disconnect();
        return undefined;
    }
    return { page, browser };
}

/**
 * @param {string} url absolute page URL including hash route
 * @param {{ port?: number, formFactor?: "mobile"|"desktop", auditPageUrl?: string }} [opts]
 */
async function runLighthouseAudit(url, opts = {}) {
    const port = opts.port ?? LH_DEBUG_PORT;
    const formFactor = opts.formFactor || "desktop";
    const flags = {
        port,
        output: ["json", "html"],
        logLevel: "error",
    };
    const config = buildLhConfig(formFactor);

    // Gatherer flake (for example Network.getResponseBody on a
    // service-worker-served document, or the target navigating mid-gather)
    // can null an entire category score. Retry a couple of times so a
    // transient protocol error does not fail the budget.
    for (let attempt = 0; attempt < 3; attempt++) {
        let attached;
        try {
            attached = await findAuditablePage(url, port);
        } catch {
            attached = undefined;
        }
        let runnerResult;
        try {
            runnerResult = attached
                ? await lighthouseModule.navigation(attached.page, url, { config, flags })
                : await lighthouse(url, flags, config);
        } finally {
            if (attached) {
                await attached.browser.disconnect();
            }
        }

        if (!runnerResult || !runnerResult.lhr) {
            throw new Error(`Lighthouse returned no result for ${url}`);
        }
        const cats = runnerResult.lhr.categories || {};
        const missing = ["performance", "accessibility", "best-practices"].some(
            (key) => cats[key] == null || cats[key].score == null
        );
        if (!missing) {
            return runnerResult;
        }
        if (attempt === 2) {
            // Let callers retry a partial report the same way they retry a
            // killed gather: a mid-gather navigation is the usual cause.
            throw new Error(`Lighthouse returned missing category scores for ${url} (transient gather failure)`);
        }
    }
}

function scoresFromLhr(lhr) {
    const cats = lhr.categories || {};
    const score = (key) => {
        const raw = cats[key] && cats[key].score;
        if (raw === null || raw === undefined) {
            return null;
        }
        return Math.round(raw * 100);
    };
    return {
        performance: score("performance"),
        accessibility: score("accessibility"),
        "best-practices": score("best-practices"),
    };
}

function vitalsFromLhr(lhr) {
    const m = lhr.audits || {};
    const display = (id) => (m[id] && m[id].displayValue ? m[id].displayValue : null);
    return {
        fcp: display("first-contentful-paint"),
        lcp: display("largest-contentful-paint"),
        tbt: display("total-blocking-time"),
        cls: display("cumulative-layout-shift"),
        si: display("speed-index"),
        tti: display("interactive"),
    };
}

function assertBudgets(scores, budgets, pageId) {
    const failures = [];
    for (const [key, min] of Object.entries(budgets)) {
        const actual = scores[key];
        if (actual === null || actual === undefined) {
            failures.push(`${key}: missing score`);
            continue;
        }
        if (actual < min) {
            failures.push(`${key}: ${actual} < ${min}`);
        }
    }
    if (failures.length > 0) {
        throw new Error(`Lighthouse budgets failed for ${pageId}: ${failures.join("; ")}`);
    }
}

function writeReports(pageId, runnerResult) {
    fs.mkdirSync(REPORT_DIR, { recursive: true });
    const safe = String(pageId).replace(/[^a-zA-Z0-9_-]/g, "_");
    const jsonPath = path.join(REPORT_DIR, `${safe}.json`);
    const htmlPath = path.join(REPORT_DIR, `${safe}.html`);
    const report = runnerResult.report;
    const html = Array.isArray(report) ? report.find((r) => r.includes("<html")) || report[1] : report;
    const json = JSON.stringify(runnerResult.lhr, null, 2);
    fs.writeFileSync(jsonPath, json);
    if (typeof html === "string") {
        fs.writeFileSync(htmlPath, html);
    }
    return { jsonPath, htmlPath };
}

module.exports = {
    LH_DEBUG_PORT,
    REPORT_DIR,
    buildLhConfig,
    runLighthouseAudit,
    scoresFromLhr,
    vitalsFromLhr,
    assertBudgets,
    writeReports,
};
