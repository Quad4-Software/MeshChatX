import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { describe, expect, it } from "vitest";
import { readPackagedAppVersion } from "../../electron/appVersion.js";

const repoRoot = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "..");

function readJson(relPath) {
    return JSON.parse(fs.readFileSync(path.join(repoRoot, relPath), "utf8"));
}

describe("electron/appVersion", () => {
    it("reads the synced package.json version from electron/app-version.json", () => {
        const pkgVersion = readJson("package.json").version;
        const appVersion = readJson("electron/app-version.json").version;
        expect(pkgVersion).toMatch(/^\d+\.\d+\.\d+/);
        expect(appVersion).toBe(pkgVersion);
        expect(readPackagedAppVersion("0.0.0")).toBe(pkgVersion);
    });
});
