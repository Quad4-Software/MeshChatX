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

        // The WebKit sandbox may only be disabled behind a guard: an
        // explicit MESHCHAT_WEBKIT_SANDBOX opt-out or a failed bwrap
        // probe, never unconditionally. Every dangerous export must be
        // indented inside a conditional block.
        expect(appRun).toContain("MESHCHAT_WEBKIT_SANDBOX");
        expect(appRun).toContain("bwrap");
        const dangerousExports = appRun
            .split("\n")
            .filter((line) => line.includes("WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS=1"));
        expect(dangerousExports.length).toBeGreaterThan(0);
        for (const line of dangerousExports) {
            expect(line).toMatch(/^\s+export\s/);
        }

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

    it("linux GTK application id stays com.meshchatx.app across packaging", () => {
        // WebKit names the a11y bus "<app id>.Sandboxed.WebProcess-<uuid>"
        // and the flatpak portal refuses names outside the sandbox app id,
        // so the shell's GApplication id must equal the manifest app-id.
        const manifest = JSON.parse(fs.readFileSync(path.join(ROOT, "packaging/flatpak/manifest.json"), "utf8"));
        expect(manifest["app-id"]).toBe("com.meshchatx.app");

        // The WebKit sandbox stays enabled; the a11y fix is the correct id,
        // not WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS.
        expect(manifest["finish-args"]).toContain("--env=WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS=0");
        expect(manifest["finish-args"].join(" ")).not.toContain("WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS=1");

        // StartupWMClass in every shipped desktop file matches the id so
        // windows group with the launcher on Wayland and X11.
        const flatpakDesktop = fs.readFileSync(
            path.join(ROOT, "packaging/flatpak/com.meshchatx.app.desktop"),
            "utf8"
        );
        const archDesktop = fs.readFileSync(
            path.join(ROOT, "packaging/arch/reticulum-meshchatx.desktop"),
            "utf8"
        );
        for (const desktop of [flatpakDesktop, archDesktop]) {
            expect(desktop).toContain("StartupWMClass=com.meshchatx.app");
        }

        // main.go must pass the env-aware id to Wails, with FLATPAK_ID
        // winning inside a sandbox and the packaged id everywhere else.
        const mainGo = read("main.go");
        expect(mainGo).toContain("ApplicationID: linuxApplicationID()");
        expect(mainGo).toContain('os.Getenv("FLATPAK_ID")');
        expect(mainGo).toContain('defaultUniqueID = "com.meshchatx.app"');
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
