#!/usr/bin/env node
/**
 * Aggregate UI metrics from test-results/ and compare against the checked-in
 * baseline at tests/ui/baseline.json.
 *
 * Reads:
 *   test-results/perf/<page>.json        -> {fcpMs,lcpMs,domContentLoadedMs,loadMs,navMs,heapUsedMb,heapTotalMb,requestCount,failedRequests}
 *   test-results/heap/<page>.json        -> {heapDeltaMb-equivalent heapDelta bytes, nodes, listeners, timeouts, intervals, rafs}
 *   test-results/lighthouse/<page>.json  -> full LHR (categories + audit details)
 *
 * Usage:
 *   node scripts/ui/metrics-check.mjs           # compare against baseline, exit 1 on regression
 *   node scripts/ui/metrics-check.mjs --update  # write current results as the new baseline
 *   node scripts/ui/metrics-check.mjs --report  # print a table without failing
 *
 * Regression semantics: a metric regresses when it exceeds baseline * (1 + tolerance).
 * Tolerances live in TOLERANCE below (fraction). Lighthouse category scores
 * regress when they drop below baseline - scoreTolerance.
 */

import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "../..");
const RESULTS_DIR = process.env.MESHCHAT_METRICS_DIR
    ? path.resolve(process.env.MESHCHAT_METRICS_DIR)
    : path.join(ROOT, "test-results");
const BASELINE_FILE = process.env.MESHCHAT_METRICS_BASELINE
    ? path.resolve(process.env.MESHCHAT_METRICS_BASELINE)
    : path.join(ROOT, "tests", "ui", "baseline.json");
const HISTORY_FILE = path.join(RESULTS_DIR, "metrics", "history.jsonl");

const TOLERANCE = {
    // time-based perf metrics (ms, mb, counts): 25% slack
    fcpMs: 0.25,
    lcpMs: 0.25,
    domContentLoadedMs: 0.25,
    loadMs: 0.25,
    navMs: 0.4,
    heapUsedMb: 0.3,
    heapTotalMb: 0.3,
    requestCount: 0.5,
    failedRequests: 0, // any new failed request regresses
    // heap-leak counters
    heapDelta: 0.5,
    nodes: 0.5,
    listeners: 0.5,
    timeouts: 0,
    intervals: 0,
    rafs: 0,
};
const SCORE_TOLERANCE = 10; // lighthouse category points

function readJson(file) {
    try {
        return JSON.parse(fs.readFileSync(file, "utf8"));
    } catch {
        return null;
    }
}

function collectPerf() {
    const dir = path.join(RESULTS_DIR, "perf");
    const out = {};
    if (!fs.existsSync(dir)) return out;
    for (const f of fs.readdirSync(dir)) {
        if (!f.endsWith(".json")) continue;
        const j = readJson(path.join(dir, f));
        if (!j) continue;
        const page = f.replace(/\.json$/, "");
        out[page] = {};
        for (const k of Object.keys(TOLERANCE)) {
            if (typeof j[k] === "number") out[page][k] = j[k];
        }
        if (typeof j.heapDelta === "number") out[page].heapDelta = j.heapDelta;
    }
    return out;
}

function collectHeap() {
    const dir = path.join(RESULTS_DIR, "heap");
    const out = {};
    if (!fs.existsSync(dir)) return out;
    for (const f of fs.readdirSync(dir)) {
        if (!f.endsWith(".json")) continue;
        const j = readJson(path.join(dir, f));
        if (!j) continue;
        const page = f.replace(/\.json$/, "");
        out[page] = {};
        for (const k of ["heapDelta", "nodes", "listeners", "timeouts", "intervals", "rafs"]) {
            if (typeof j[k] === "number") out[page][`heap_${k}`] = j[k];
        }
    }
    return out;
}

function collectLighthouse() {
    const dir = path.join(RESULTS_DIR, "lighthouse");
    const out = {};
    if (!fs.existsSync(dir)) return out;
    for (const f of fs.readdirSync(dir)) {
        if (!f.endsWith(".json")) continue;
        const lhr = readJson(path.join(dir, f));
        if (!lhr || !lhr.categories) continue;
        const page = f.replace(/\.json$/, "");
        const row = {};
        for (const [key, cat] of Object.entries(lhr.categories)) {
            if (typeof cat.score === "number") row[`lh_${key}`] = Math.round(cat.score * 100);
        }
        for (const [audit, key] of [
            ["first-contentful-paint", "lh_fcpMs"],
            ["largest-contentful-paint", "lh_lcpMs"],
            ["total-blocking-time", "lh_tbtMs"],
            ["cumulative-layout-shift", "lh_cls"],
            ["speed-index", "lh_speedIndexMs"],
        ]) {
            const a = lhr.audits && lhr.audits[audit];
            if (a && typeof a.numericValue === "number") {
                row[key] = Math.round(a.numericValue * (key === "lh_cls" ? 1000 : 1)) / (key === "lh_cls" ? 1000 : 1);
            }
        }
        out[page] = row;
    }
    return out;
}

function gitRev() {
    try {
        return execSync("git rev-parse --short HEAD", { cwd: ROOT }).toString().trim();
    } catch {
        return "unknown";
    }
}

function collectAll() {
    const rows = {};
    for (const [kind, data] of [
        ["perf", collectPerf()],
        ["heap", collectHeap()],
        ["lighthouse", collectLighthouse()],
    ]) {
        for (const [page, metrics] of Object.entries(data)) {
            rows[page] = { ...(rows[page] || {}), ...metrics };
        }
    }
    return rows;
}

function compare(current, baseline) {
    const regressions = [];
    const improvements = [];
    const newPages = [];
    for (const [page, metrics] of Object.entries(current)) {
        const base = baseline.pages?.[page];
        if (!base) {
            newPages.push(page);
            continue;
        }
        for (const [key, val] of Object.entries(metrics)) {
            const b = base[key];
            if (typeof b !== "number") continue;
            if (key.startsWith("lh_") && !key.endsWith("Ms") && key !== "lh_cls") {
                // lighthouse score: lower is worse
                if (val < b - SCORE_TOLERANCE) {
                    regressions.push(`${page}.${key}: ${b} -> ${val} (score drop)`);
                } else if (val > b + SCORE_TOLERANCE) {
                    improvements.push(`${page}.${key}: ${b} -> ${val}`);
                }
                continue;
            }
            const tol = TOLERANCE[key] ?? TOLERANCE[key.replace(/^heap_/, "")] ?? 0.25;
            const limit = b * (1 + tol) + (tol === 0 ? 0 : 0);
            if (val > limit && val - b > 0) {
                regressions.push(`${page}.${key}: ${b} -> ${val} (limit ${Math.round(limit * 100) / 100})`);
            } else if (val < b * (1 - Math.min(tol, 0.5))) {
                improvements.push(`${page}.${key}: ${b} -> ${val}`);
            }
        }
    }
    const missingPages = Object.keys(baseline.pages || {}).filter((p) => !current[p]);
    return { regressions, improvements, newPages, missingPages };
}

function main() {
    const args = process.argv.slice(2);
    const update = args.includes("--update");
    const reportOnly = args.includes("--report");

    const current = collectAll();
    if (Object.keys(current).length === 0) {
        console.log("metrics-check: no test-results found, nothing to compare");
        process.exit(reportOnly || update ? 1 : 0);
    }

    const run = {
        ts: new Date().toISOString(),
        git: gitRev(),
        pages: current,
    };

    fs.mkdirSync(path.dirname(HISTORY_FILE), { recursive: true });
    fs.appendFileSync(HISTORY_FILE, JSON.stringify(run) + "\n");

    if (update) {
        fs.writeFileSync(
            BASELINE_FILE,
            JSON.stringify({ updatedAt: run.ts, git: run.git, pages: current }, null, 2) + "\n"
        );
        console.log(`metrics-check: baseline updated (${Object.keys(current).length} pages)`);
        return;
    }

    const baseline = readJson(BASELINE_FILE);
    if (!baseline) {
        console.log("metrics-check: no baseline.json found - run with --update to create one");
        process.exit(reportOnly ? 0 : 1);
    }

    const { regressions, improvements, newPages, missingPages } = compare(current, baseline);

    // Compact table output
    const keys = [...new Set(Object.values(current).flatMap((m) => Object.keys(m)))].sort();
    const pages = Object.keys(current).sort();
    console.log(`metrics-check vs baseline ${baseline.git || "?"} (${baseline.updatedAt || "?"})`);
    console.log("");
    for (const key of keys) {
        const row = pages.map((p) => {
            const cur = current[p][key];
            const base = baseline.pages?.[p]?.[key];
            if (cur === undefined) return null;
            const delta = typeof base === "number" ? ` (${cur > base ? "+" : ""}${Math.round((cur - base) * 100) / 100})` : " (new)";
            return `${p}: ${cur}${delta}`;
        });
        if (row.filter(Boolean).length) {
            console.log(`  ${key}`);
            for (const r of row) if (r) console.log(`    ${r}`);
        }
    }
    console.log("");
    if (newPages.length) console.log(`  new pages (no baseline): ${newPages.join(", ")}`);
    if (missingPages.length) console.log(`  baseline pages missing this run: ${missingPages.join(", ")}`);
    if (improvements.length) {
        console.log("  improvements:");
        for (const i of improvements) console.log(`    ${i}`);
    }
    if (regressions.length) {
        console.log("  REGRESSIONS:");
        for (const r of regressions) console.log(`    ${r}`);
        if (!reportOnly) process.exit(1);
    } else {
        console.log("  no regressions");
    }
}

main();
