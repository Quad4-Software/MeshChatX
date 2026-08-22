const fs = require("fs");
const path = require("path");
const lighthouseModule = require("lighthouse");
const lighthouse = lighthouseModule.default || lighthouseModule;
const desktopConfig = lighthouseModule.desktopConfig;

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
            blockedUrlPatterns: [
                "*://*/ws",
                "*://*/ws?*",
                "ws://*/*",
                "wss://*/*",
                "*service-worker.js*",
            ],
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
 * @param {string} url absolute page URL including hash route
 * @param {{ port?: number, formFactor?: "mobile"|"desktop" }} [opts]
 */
async function runLighthouseAudit(url, opts = {}) {
    const port = opts.port ?? LH_DEBUG_PORT;
    const formFactor = opts.formFactor || "desktop";

    const runnerResult = await lighthouse(
        url,
        {
            port,
            output: ["json", "html"],
            logLevel: "error",
        },
        buildLhConfig(formFactor)
    );

    if (!runnerResult || !runnerResult.lhr) {
        throw new Error(`Lighthouse returned no result for ${url}`);
    }

    return runnerResult;
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
