// SPDX-License-Identifier: 0BSD
// Contract tests for the Wails desktop packaging tree (desktop/build).
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const DESKTOP = path.join(ROOT, "desktop");
const read = (p) => fs.readFileSync(path.join(DESKTOP, p), "utf8");

describe("desktop packaging contracts", () => {
    it("build/config.yml identifies the app and info", () => {
        const y = read("build/config.yml");
        expect(y).toContain("Reticulum MeshChatX");
        expect(y).toContain("com.meshchatx.app");
    });

    it("linux nfpm packages the binary, icon, desktop file and backend", () => {
        const nfpm = read("build/linux/nfpm/nfpm.yaml");
        expect(nfpm).toContain("./bin/meshchatx-desktop");
        expect(nfpm).toContain("./bin/backend");
        expect(nfpm).toContain("libgtk-4-1");
        expect(nfpm).toContain("libwebkitgtk-6.0-4");
        const task = read("build/linux/Taskfile.yml");
        expect(task).toContain("create:appimage");
        expect(task).toContain("create:deb");
        expect(task).toContain("create:zip");
        expect(task).toContain("x-scheme-handler/lxmf");
        expect(task).toContain("x-scheme-handler/rns");
    });

    it("windows nsis registers lxmf/rns protocol handlers", () => {
        const nsi = read("build/windows/nsis/project.nsi");
        expect(nsi).toContain('WriteRegStr HKCR "lxmf"');
        expect(nsi).toContain('WriteRegStr HKCR "rns"');
        expect(nsi).toContain("bin\\backend");
    });

    it("macOS bundle declares URL schemes and backend resource dir", () => {
        const plist = read("build/darwin/Info.plist");
        expect(plist).toContain("<string>lxmf</string>");
        expect(plist).toContain("<string>rns</string>");
        expect(plist).toContain("com.meshchatx.app");
        const task = read("build/darwin/Taskfile.yml");
        expect(task).toContain("Contents/Resources/backend");
    });

    it("backend bundling lands beside the shell binary", () => {
        // paths.go must keep resolving <exeDir>/backend/ReticulumMeshChatX.
        const paths = fs.readFileSync(path.join(DESKTOP, "internal", "paths", "paths.go"), "utf8");
        expect(paths).toContain(`"backend"`);
        expect(paths).toContain("ReticulumMeshChatX");
    });

    it("appimage build ships a real AppRun, pinned tools and sane exclusions", () => {
        const dir = path.join(DESKTOP, "build/linux/appimage");
        const appRun = fs.readFileSync(path.join(dir, "AppRun"), "utf8");
        const build = fs.readFileSync(path.join(dir, "build.sh"), "utf8");
        const tools = fs.readFileSync(path.join(dir, "tools.tsv"), "utf8");
        const exclude = fs.readFileSync(path.join(dir, "excludelist.txt"), "utf8");

        // AppRun must exist, be executable, preserve $APPIMAGE and cd into
        // $APPDIR (patched WebKit helper paths are relative to it).
        expect(fs.statSync(path.join(dir, "AppRun")).mode & 0o111).toBeTruthy();
        expect(appRun).toContain("APPDIR");
        expect(appRun).toContain('cd "$APPDIR"');
        expect(appRun).not.toContain("WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS=1");

        // Tools are pinned by sha256 in tools.tsv; build.sh verifies before use.
        expect(tools).toContain("linuxdeploy\tfile\thttps://github.com/linuxdeploy/");
        expect(tools).toContain("appimagetool\tfile\thttps://github.com/AppImage/");
        expect(tools).toMatch(/[0-9a-f]{64}/);
        expect(build).toContain("sha256sum");
        expect(build).toContain("ALLOW_UNPINNED_TOOLS");

        // Heavy scratch must stay out of the shared /tmp tmpfs.
        expect(build).toContain("TMPDIR=");

        // Excludelist documents the no-glibc / no-GPU-driver policy.
        expect(exclude).toMatch(/libc\.so/);
        expect(exclude).toMatch(/libGL|libEGL/);

        // The generated .desktop entry registers both URL schemes.
        expect(build).toContain("x-scheme-handler/lxmf");
        expect(build).toContain("x-scheme-handler/rns");

        // WebKitGTK helper path patching is part of the pipeline.
        expect(fs.existsSync(path.join(dir, "patch-webkitgtk.py"))).toBe(true);
    });

    it("no electron packaging remains in package.json", () => {
        const pkg = JSON.parse(fs.readFileSync(path.join(ROOT, "package.json"), "utf8"));
        const blob = JSON.stringify({
            scripts: pkg.scripts,
            devDependencies: pkg.devDependencies,
            dependencies: pkg.dependencies,
            build: pkg.build,
        });
        expect(blob).not.toMatch(
            /electron-builder|electron-builder-squirrel|@electron\/fuses|electron-prompt|"electron"/
        );
        expect(pkg.scripts["desktop:build"]).toBeTruthy();
        expect(pkg.scripts["dist:linux"]).toBeTruthy();
    });
});
