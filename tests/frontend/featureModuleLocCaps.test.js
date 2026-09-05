// SPDX-License-Identifier: 0BSD

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = resolve(import.meta.dirname, "../..");
const FEATURES_ROOT = join(ROOT, "meshchatx", "src", "frontend", "features");

const PAGE_SHELL_HARD_CAP = 800;
const LEAF_SVELTE_HARD_CAP = 400;
const LIB_TS_HARD_CAP = 500;

/** Treated as shells (hard 800) even if not named *Page.svelte. */
const SHELL_LIKE_SVELTE = new Set(["ConversationViewer.svelte"]);

/**
 * Pre-existing legacy leaves over the leaf cap.
 * Tracked for follow-up splits, not Wave A/B regressions.
 */
const LEGACY_LEAF_ALLOWLIST = new Set([
    "ConversationMessageEntry.svelte",
    "MessagesSidebar.svelte",
    "ConversationPeerHeader.svelte",
]);

/** Legacy page shells still above hard cap, follow-up split required. */
const LEGACY_PAGE_ALLOWLIST = new Set(["MessagesPage.svelte", "MapPage.svelte", "SettingsPage.svelte"]);

/** Pre-existing lib files over the cap. */
const LEGACY_LIB_ALLOWLIST = new Set([
    "defaultContent.ts",
    "appShellLifecycle.ts",
    "tutorialState.svelte.ts",
]);

/** Viewer shell still above 800 after host split, fail if it grows past 1000. */
const LEGACY_SHELL_ALLOWLIST = new Set(["ConversationViewer.svelte"]);
const LEGACY_SHELL_REGRESSION_CAP = 1000;

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
            const base = filePath.split("/").pop();
            if (filePath.endsWith("Page.svelte") || SHELL_LIKE_SVELTE.has(base)) {
                pageShells.push(item);
            } else if (!LEGACY_LEAF_ALLOWLIST.has(base)) {
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
            .filter((item) => {
                const base = item.path.split("/").pop();
                if (LEGACY_PAGE_ALLOWLIST.has(base)) {
                    return false;
                }
                if (LEGACY_SHELL_ALLOWLIST.has(base)) {
                    return item.loc > LEGACY_SHELL_REGRESSION_CAP;
                }
                return item.loc > PAGE_SHELL_HARD_CAP;
            })
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

    it("ConversationViewer shell stays under regression cap after host split", () => {
        const { pageShells } = getFeatureFiles();
        const viewer = pageShells.find((item) => item.path.endsWith("ConversationViewer.svelte"));
        expect(viewer, "ConversationViewer.svelte missing").toBeTruthy();
        expect(viewer.loc).toBeLessThanOrEqual(LEGACY_SHELL_REGRESSION_CAP);
        expect(viewer.loc).toBeLessThan(1446);
    });

    it("feature library modules under features/*/lib stay within LOC cap (500)", () => {
        const { libTs } = getFeatureFiles();
        expect(libTs.length).toBeGreaterThan(0);

        const offenders = libTs
            .filter((item) => {
                const base = item.path.split("/").pop();
                if (LEGACY_LIB_ALLOWLIST.has(base)) {
                    return false;
                }
                return item.loc > LIB_TS_HARD_CAP;
            })
            .map((item) => `${item.path}: ${item.loc} lines (cap ${LIB_TS_HARD_CAP})`);

        expect(offenders, "Feature lib TS files exceeding hard LOC cap").toEqual([]);
    });
});
