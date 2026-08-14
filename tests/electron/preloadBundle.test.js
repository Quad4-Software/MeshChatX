import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { describe, expect, it } from "vitest";

const repoRoot = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const bundlePath = path.join(repoRoot, "electron/preload.bundle.js");

describe("electron/preload.bundle", () => {
    it("exists and inlines shellOrigin for sandbox preload", () => {
        expect(fs.existsSync(bundlePath)).toBe(true);
        const source = fs.readFileSync(bundlePath, "utf8");
        expect(source).toContain("function isTrustedShellOrigin");
        expect(source).not.toContain("require(\"./shellOrigin\")");
    });
});
