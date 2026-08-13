import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const ROOT = resolve(__dirname, "../..");

function readSource(relativePath) {
    return readFileSync(resolve(ROOT, relativePath), "utf8");
}

describe("Linux AppImage packaging contracts", () => {
    it("pins the warm-script AppImage toolset to package.json", () => {
        const pkg = JSON.parse(readSource("package.json"));
        const toolset = pkg.build.toolsets.appimage;
        expect(toolset).toBe("1.0.2");

        const warm = readSource("scripts/ci/github-warm-appimage-tools.sh");
        expect(warm).toContain(`APPIMAGE_TOOLSET="${toolset}"`);
        expect(warm).toContain("FILENAME=\"appimage-tools-runtime-20251108.tar.gz\"");
        expect(warm).toContain("SHA256=\"a784a8c26331ec2e945c23d6bdb14af5c9df27f5939825d84b8709c61dc81eb0\"");
        expect(warm).toContain("--http1.1");
        expect(warm).toContain("--retry-all-errors");
    });

    it("warms AppImage tools before freeze and retries ECONNRESET", () => {
        const script = readSource("scripts/ci/github-build-linux-release-assets.sh");
        const warmAt = script.indexOf("github-warm-appimage-tools.sh");
        const freezeAt = script.indexOf("PLATFORM=linux ARCH=x64 pnpm run build");
        const retryAt = script.indexOf("run_electron_builder --linux");
        expect(warmAt).toBeGreaterThan(-1);
        expect(freezeAt).toBeGreaterThan(warmAt);
        expect(retryAt).toBeGreaterThan(freezeAt);
        expect(script).toContain("ECONNRESET");
        expect(script).toContain("run_electron_builder()");
    });

    it("caches electron-builder toolsets on Linux package and release jobs", () => {
        const linux = readSource(".github/workflows/build-linux-packages.yml");
        const release = readSource(".github/workflows/build-release.yml");
        expect(linux).toContain("Cache electron-builder toolsets");
        expect(linux).toContain("~/.cache/electron-builder");
        expect(release).toContain("Cache electron-builder toolsets");
        expect(release).toContain("~/.cache/electron-builder");

        const linuxBuild = linux.slice(linux.indexOf("- name: Build release-assets"), linux.indexOf("- name: Build release-assets") + 400);
        const releaseBuild = release.slice(
            release.indexOf("- name: Build release-assets"),
            release.indexOf("- name: Build release-assets") + 400
        );
        expect(linuxBuild).toContain("GITHUB_TOKEN: ${{ github.token }}");
        expect(releaseBuild).toContain("GITHUB_TOKEN: ${{ github.token }}");
        expect(linuxBuild).toContain("github-build-linux-release-assets.sh");
        expect(releaseBuild).toContain("github-build-linux-release-assets.sh");
    });
});
