import { readFileSync, readdirSync, statSync } from "fs";
import { join } from "path";
import { describe, it, expect } from "vitest";

const FRONTEND_ROOT = join(process.cwd(), "meshchatx/src/frontend");
const SKIP_DIRS = new Set(["public", "node_modules"]);
const SOURCE_EXT = /\.(vue|js)$/;

function collectSourceFiles(dir, acc = []) {
    for (const name of readdirSync(dir)) {
        const path = join(dir, name);
        const stat = statSync(path);
        if (stat.isDirectory()) {
            if (SKIP_DIRS.has(name)) {
                continue;
            }
            collectSourceFiles(path, acc);
        } else if (SOURCE_EXT.test(name)) {
            acc.push(path);
        }
    }
    return acc;
}

function relativePath(path) {
    return path.replace(`${process.cwd()}/`, "");
}

describe("API client usage guard", () => {
    it("does not use raw fetch for mutating /api/v1 requests", () => {
        const offenders = [];
        for (const file of collectSourceFiles(FRONTEND_ROOT)) {
            if (file.endsWith("/js/apiClient.js")) {
                continue;
            }
            const src = readFileSync(file, "utf8");
            if (!src.includes("/api/v1") || !src.includes("fetch(")) {
                continue;
            }
            if (/fetch\s*\([\s\S]{0,400}?\/api\/v1[\s\S]{0,400}?method\s*:\s*["'](POST|PUT|PATCH|DELETE)["']/i.test(src)) {
                offenders.push(relativePath(file));
            }
        }
        expect(offenders).toEqual([]);
    });
});
