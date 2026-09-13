import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const ROOT = resolve(__dirname, "../..");

function readSource(relativePath) {
    return readFileSync(resolve(ROOT, relativePath), "utf8");
}

describe("filesync packaging contracts", () => {
    it("docker ignore excludes rns_filesync non-runtime trees", () => {
        const dockerignore = readSource(".dockerignore");
        expect(dockerignore).toContain("vendor/rns_filesync/tests/");
        expect(dockerignore).toContain("vendor/rns_filesync/docker/");
        expect(dockerignore).toContain("vendor/rns_filesync/packaging/");
        expect(dockerignore).toContain("vendor/rns_filesync/sideband/");
    });

    it("package verify denylist covers rns_filesync bloat paths", () => {
        const script = readSource("scripts/ci/verify-package-contents.sh");
        expect(script).toContain("vendor/rns_filesync/tests");
        expect(script).toContain("vendor/rns_filesync/docker");
        expect(script).toContain("vendor/rns_filesync/packaging");
    });

    it("tools registry exposes filesync without comingSoon", () => {
        const tools = readSource("meshchatx/src/frontend/js/registries/coreToolsEntries.ts");
        expect(tools).toContain('name: "rns-filesync"');
        expect(tools).toContain('route: { name: "rns-filesync" }');
        const block = tools.slice(tools.indexOf('name: "rns-filesync"'), tools.indexOf('name: "rnsh"'));
        expect(block).not.toContain("comingSoon");
        expect(block).toContain("alpha: true");
    });
});
