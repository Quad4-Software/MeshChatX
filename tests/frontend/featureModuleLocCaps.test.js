// SPDX-License-Identifier: 0BSD

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = resolve(import.meta.dirname, "../..");
const FEATURES_ROOT = join(ROOT, "meshchatx", "src", "frontend", "features");

const PAGE_SHELL_HARD_CAP = 800;
const LEAF_SVELTE_HARD_CAP = 400;
const LIB_TS_HARD_CAP = 500;

/**
 * Counts total lines using wc -l newline split convention.
 * Trailing empty line after final newline is not counted as extra line.
 */
function countLines(content) {
    if (!content) {
        return 0;
    }
    const lines = content.split(/\r?\n/);
    if (lines.length > 0 && lines[lines.length - 1] === "") {
        return lines.length - 1;
    }
    return lines.length;
}

/**
 * Recursively collects file paths while skipping node_modules and hidden folders.
 */
function walkFiles(dir, fileList = []) {
    const entries = readdirSync(dir);
    for (const entry of entries) {
        if (entry === "node_modules" || entry.startsWith(".")) {
            continue;
        }
        const fullPath = join(dir, entry);
        const stat = statSync(fullPath);
        if (stat.isDirectory()) {
            walkFiles(fullPath, fileList);
        } else {
            fileList.push(fullPath);
        }
    }
    return fileList;
}

function getFeatureFiles() {
    const allFiles = walkFiles(FEATURES_ROOT);
    const pageShells = [];
    const leafSvelte = [];
    const libTs = [];

    for (const filePath of allFiles) {
        const relPath = relative(ROOT, filePath);
        const content = readFileSync(filePath, "utf8");
        const loc = countLines(content);
        const item = { path: relPath, loc };

        if (filePath.endsWith(".svelte")) {
            if (filePath.endsWith("Page.svelte")) {
                pageShells.push(item);
            } else {
                leafSvelte.push(item);
            }
        } else if (filePath.includes("/lib/") && filePath.endsWith(".ts")) {
            libTs.push(item);
        }
    }

    return { pageShells, leafSvelte, libTs };
}

describe("feature module LOC caps oracle", () => {
    it("page shell components under features stay within hard LOC cap (800)", () => {
        const { pageShells } = getFeatureFiles();
        expect(pageShells.length).toBeGreaterThan(0);

        const offenders = pageShells
            .filter((item) => item.loc > PAGE_SHELL_HARD_CAP)
            .map((item) => `${item.path}: ${item.loc} lines (cap ${PAGE_SHELL_HARD_CAP})`);

        expect(offenders, "Page shells exceeding hard LOC cap").toEqual([]);
    });

    it("non-page svelte components under features stay within leaf LOC cap (400)", () => {
        const { leafSvelte } = getFeatureFiles();
        expect(leafSvelte.length).toBeGreaterThan(0);

        const offenders = leafSvelte
            .filter((item) => item.loc > LEAF_SVELTE_HARD_CAP)
            .map((item) => `${item.path}: ${item.loc} lines (cap ${LEAF_SVELTE_HARD_CAP})`);

        expect(offenders, "Leaf Svelte components exceeding hard LOC cap").toEqual([]);
    });

    it("feature library modules under features/*/lib stay within LOC cap (500)", () => {
        const { libTs } = getFeatureFiles();
        expect(libTs.length).toBeGreaterThan(0);

        const offenders = libTs
            .filter((item) => item.loc > LIB_TS_HARD_CAP)
            .map((item) => `${item.path}: ${item.loc} lines (cap ${LIB_TS_HARD_CAP})`);

        expect(offenders, "Feature lib TS files exceeding hard LOC cap").toEqual([]);
    });
});
