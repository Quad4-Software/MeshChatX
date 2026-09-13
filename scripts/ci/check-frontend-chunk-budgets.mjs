#!/usr/bin/env node
// SPDX-License-Identifier: 0BSD
/**
 * Fail CI when named Vite JS chunks under meshchatx/public/assets exceed budgets.
 * Requires a prior pnpm run build-frontend (or equivalent) so assets exist.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "../..");
const assetsDir = path.join(repoRoot, "meshchatx/public/assets");
const budgetsPath = path.join(__dirname, "frontend-chunk-budgets.json");

function fail(message) {
    console.error(message);
    process.exit(1);
}

if (!fs.existsSync(assetsDir)) {
    fail(`Missing built assets at ${assetsDir}. Run pnpm run build-frontend first.`);
}

if (!fs.existsSync(budgetsPath)) {
    fail(`Missing budgets file at ${budgetsPath}`);
}

const budgets = JSON.parse(fs.readFileSync(budgetsPath, "utf8"));
const chunkBudgets = Array.isArray(budgets.chunks) ? budgets.chunks : [];
if (chunkBudgets.length === 0) {
    fail("frontend-chunk-budgets.json has no chunks entries");
}

const jsFiles = fs.readdirSync(assetsDir).filter((name) => name.endsWith(".js"));
if (jsFiles.length === 0) {
    fail(`No .js chunks found in ${assetsDir}`);
}

const failures = [];
const report = [];

for (const entry of chunkBudgets) {
    const prefix = String(entry.prefix || "");
    const maxKiB = Number(entry.maxKiB);
    if (!prefix || !Number.isFinite(maxKiB) || maxKiB <= 0) {
        failures.push(`Invalid budget entry: ${JSON.stringify(entry)}`);
        continue;
    }
    const matches = jsFiles
        .filter((name) => {
            if (!name.startsWith(prefix)) {
                return false;
            }
            // Prefer longer prefixes (vendor-foo-bar- over vendor-foo-).
            const longerOwns = chunkBudgets.some(
                (other) =>
                    other.prefix !== prefix &&
                    String(other.prefix).startsWith(prefix) &&
                    name.startsWith(String(other.prefix))
            );
            return !longerOwns;
        })
        .map((name) => {
            const full = path.join(assetsDir, name);
            return { name, size: fs.statSync(full).size };
        })
        .sort((a, b) => b.size - a.size);

    if (matches.length === 0) {
        failures.push(`No chunk matching prefix ${prefix}`);
        continue;
    }

    const largest = matches[0];
    const sizeKiB = largest.size / 1024;
    report.push({
        prefix,
        file: largest.name,
        sizeKiB: Number(sizeKiB.toFixed(2)),
        maxKiB,
        ok: sizeKiB <= maxKiB,
    });
    if (sizeKiB > maxKiB) {
        failures.push(`${prefix} ${largest.name} is ${sizeKiB.toFixed(2)} KiB (budget ${maxKiB} KiB)`);
    }
}

for (const row of report) {
    const mark = row.ok ? "ok" : "FAIL";
    console.log(
        `${mark.padEnd(4)} ${row.prefix.padEnd(22)} ${String(row.sizeKiB).padStart(8)} / ${row.maxKiB} KiB  (${row.file})`
    );
}

if (failures.length > 0) {
    fail(`Frontend chunk budget check failed:\n${failures.map((f) => `  - ${f}`).join("\n")}`);
}

console.log(`Frontend chunk budgets OK (${report.length} prefixes).`);
