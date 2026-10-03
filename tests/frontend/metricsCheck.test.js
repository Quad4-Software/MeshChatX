// Vitest for scripts/ui/metrics-check.mjs regression detection.
import { describe, it, expect } from "vitest";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const SCRIPT = path.resolve(__dirname, "../../scripts/ui/metrics-check.mjs");

function mkEnv(resultsDir, baselineFile) {
    return {
        ...process.env,
        MESHCHAT_METRICS_DIR: resultsDir,
        MESHCHAT_METRICS_BASELINE: baselineFile,
    };
}

function runCheck(resultsDir, baselineFile, args = []) {
    try {
        const out = execFileSync(process.execPath, [SCRIPT, ...args], {
            env: mkEnv(resultsDir, baselineFile),
            encoding: "utf8",
            stdio: ["ignore", "pipe", "pipe"],
        });
        return { code: 0, out };
    } catch (e) {
        return { code: e.status ?? 1, out: `${e.stdout || ""}${e.stderr || ""}` };
    }
}

function writeResults(dir, pages) {
    fs.mkdirSync(path.join(dir, "perf"), { recursive: true });
    for (const [page, metrics] of Object.entries(pages)) {
        fs.writeFileSync(path.join(dir, "perf", `${page}.json`), JSON.stringify(metrics));
    }
}

describe("metrics-check", () => {
    it("updates baseline then passes when unchanged", () => {
        const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "mcx-metrics-"));
        const results = path.join(tmp, "results");
        const baseline = path.join(tmp, "baseline.json");
        writeResults(results, { messages: { fcpMs: 100, lcpMs: 200, heapUsedMb: 10 } });

        const upd = runCheck(results, baseline, ["--update"]);
        expect(upd.code).toBe(0);
        expect(fs.existsSync(baseline)).toBe(true);
        const saved = JSON.parse(fs.readFileSync(baseline, "utf8"));
        expect(saved.pages.messages.fcpMs).toBe(100);

        const chk = runCheck(results, baseline);
        expect(chk.code).toBe(0);
        expect(chk.out).toMatch(/no regressions/);
    });

    it("fails when a perf metric regresses beyond tolerance", () => {
        const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "mcx-metrics-"));
        const results = path.join(tmp, "results");
        const baseline = path.join(tmp, "baseline.json");
        writeResults(results, { messages: { fcpMs: 100 } });
        runCheck(results, baseline, ["--update"]);

        writeResults(results, { messages: { fcpMs: 400 } });
        const chk = runCheck(results, baseline);
        expect(chk.code).toBe(1);
        expect(chk.out).toMatch(/REGRESSIONS/);
        expect(chk.out).toMatch(/messages\.fcpMs/);
    });

    it("fails when a lighthouse score drops beyond tolerance", () => {
        const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "mcx-metrics-"));
        const results = path.join(tmp, "results");
        const baseline = path.join(tmp, "baseline.json");

        const lhDir = path.join(results, "lighthouse");
        fs.mkdirSync(lhDir, { recursive: true });
        const lhr = { categories: { performance: { score: 0.9 } }, audits: {} };
        fs.writeFileSync(path.join(lhDir, "about.json"), JSON.stringify(lhr));
        runCheck(results, baseline, ["--update"]);

        lhr.categories.performance.score = 0.5;
        fs.writeFileSync(path.join(lhDir, "about.json"), JSON.stringify(lhr));
        const chk = runCheck(results, baseline);
        expect(chk.code).toBe(1);
        expect(chk.out).toMatch(/about\.lh_performance/);
    });

    it("appends history rows to history.jsonl", () => {
        const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "mcx-metrics-"));
        const results = path.join(tmp, "results");
        const baseline = path.join(tmp, "baseline.json");
        writeResults(results, { contacts: { fcpMs: 80 } });
        runCheck(results, baseline, ["--update"]);
        runCheck(results, baseline);

        const hist = path.join(results, "metrics", "history.jsonl");
        expect(fs.existsSync(hist)).toBe(true);
        const lines = fs.readFileSync(hist, "utf8").trim().split("\n");
        expect(lines.length).toBe(2);
        const row = JSON.parse(lines[0]);
        expect(row.pages.contacts.fcpMs).toBe(80);
        expect(row.git).toBeTruthy();
    });
});
