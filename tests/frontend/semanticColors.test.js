// SPDX-License-Identifier: 0BSD

// Regression guard: flags hardcoded Tailwind palette colors (bg-blue-500,
// text-gray-700, etc.) in Vue components. Semantic tokens (sem-*) or CSS
// vars should be used so themes stay consistent. A baseline file captures
// current counts — the test fails if a file's count grows or a new file
// adds hardcoded colors.
import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync } from "fs";
import { join, relative, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const COMPONENTS_ROOT = join(__dirname, "../../meshchatx/src/frontend/components");
const BASELINE_PATH = join(__dirname, "baselines/semantic-colors.json");

const HARDCODED_RE =
    /\b(?:bg|text|border|ring|divide|from|to|via|placeholder|fill|stroke|hover:bg|hover:text|dark:bg|dark:text|focus:ring|focus:border)-(?:red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|gray|grey|zinc|neutral|stone|slate)-\d{2,3}(?:\/\d+)?\b/g;

function walk(dir) {
    const out = [];
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
        const p = join(dir, entry.name);
        if (entry.isDirectory()) {
            out.push(...walk(p));
        } else if (entry.name.endsWith(".vue")) {
            out.push(p);
        }
    }
    return out;
}

function countHardcoded(path) {
    const src = readFileSync(path, "utf8");
    return (src.match(HARDCODED_RE) || []).length;
}

describe("semantic color usage", () => {
    const baseline = JSON.parse(readFileSync(BASELINE_PATH, "utf8"));
    const files = walk(COMPONENTS_ROOT);
    const current = {};
    for (const p of files) {
        const rel = relative(COMPONENTS_ROOT, p);
        const count = countHardcoded(p);
        if (count > 0) {
            current[rel] = count;
        }
    }

    it("no file increases its hardcoded color count", () => {
        const violations = [];
        for (const [file, count] of Object.entries(current)) {
            const allowed = baseline[file] || 0;
            if (count > allowed) {
                violations.push(`${file}: ${count} > baseline ${allowed}`);
            }
        }
        expect(violations, violations.join("\n")).toEqual([]);
    });

    it("no new files introduce hardcoded colors", () => {
        const newViolators = Object.keys(current).filter((f) => !(f in baseline));
        expect(
            newViolators,
            newViolators.map((f) => `${f}: use sem-* tokens instead of palette colors`).join("\n"),
        ).toEqual([]);
    });
});
