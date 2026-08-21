const fs = require("fs");
const path = require("path");
const lighthouseModule = require("lighthouse");
const lighthouse = lighthouseModule.default || lighthouseModule;

const LH_DEBUG_PORT = parseInt(process.env.LH_DEBUG_PORT || "9222", 10);
const REPORT_DIR = process.env.LH_REPORT_DIR || path.join("test-results", "lighthouse");

/**
 * @param {string} url absolute page URL including hash route
 * @param {{ port?: number, formFactor?: "mobile"|"desktop" }} [opts]
 */
async function runLighthouseAudit(url, opts = {}) {
    const port = opts.port ?? LH_DEBUG_PORT;
    const formFactor = opts.formFactor || "desktop";

    const runnerResult = await lighthouse(url, {
        port,
        output: ["json", "html"],
        logLevel: "error",
        onlyCategories: ["performance", "accessibility", "best-practices"],
        formFactor,
        screenEmulation:
            formFactor === "desktop"
                ? {
                      mobile: false,
                      width: 1350,
                      height: 940,
                      deviceScaleFactor: 1,
                      disabled: false,
                  }
                : undefined,
        throttlingMethod: "simulate",
    });

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
    runLighthouseAudit,
    scoresFromLhr,
    assertBudgets,
    writeReports,
};
