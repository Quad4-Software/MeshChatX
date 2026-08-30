// SPDX-License-Identifier: 0BSD

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = resolve(import.meta.dirname, "../..");

function readRepo(relPath) {
    return readFileSync(resolve(ROOT, relPath), "utf8");
}

describe("electron shell static assets", () => {
    it("loading.html and crash.html use compiled Tailwind 4 CSS, not vendored v3 runtime", () => {
        for (const rel of ["electron/loading.html", "electron/crash.html"]) {
            const html = readRepo(rel);
            expect(html, rel).toContain('href="./assets/css/electron-shell.css"');
            expect(html, rel).not.toContain("tailwind-v3.4.3");
            expect(html, rel).not.toContain("cdn.tailwindcss.com");
        }
    });

    it("rnode-flasher index uses the shared electron-shell.css copy", () => {
        const html = readRepo("meshchatx/src/frontend/public/rnode-flasher/index.html");
        expect(html).toContain("/assets/css/electron-shell.css");
        expect(html).not.toContain("tailwind-v3.4.3");
    });

    it("loading.html CSP allows self styles for compiled CSS", () => {
        const html = readRepo("electron/loading.html");
        const match = html.match(/http-equiv="Content-Security-Policy"[\s\S]*?content="([^"]+)"/);
        expect(match).toBeTruthy();
        expect(match[1]).toContain("style-src 'self'");
    });

    it("package.json predev and prebuild-frontend compile electron shell CSS", () => {
        const pkg = JSON.parse(readRepo("package.json"));
        expect(pkg.scripts.predev).toContain("build-electron-shell-css.mjs");
        expect(pkg.scripts["prebuild-frontend"]).toContain("build-electron-shell-css.mjs");
    });

    it("electron-shell.src.css scans shell HTML entry points", () => {
        const css = readRepo("electron/assets/css/electron-shell.src.css");
        expect(css).toContain('@source "../../loading.html"');
        expect(css).toContain('@source "../../crash.html"');
        expect(css).toContain("rnode-flasher/index.html");
    });

    it("Dockerfile frontend stage copies electron shell CSS build inputs", () => {
        for (const dockerfile of ["Dockerfile", "Dockerfile.hardened"]) {
            const docker = readRepo(dockerfile);
            expect(docker, dockerfile).toContain("scripts/build-electron-shell-css.mjs");
            expect(docker, dockerfile).toContain("electron/assets/css/electron-shell.src.css");
            expect(docker, dockerfile).toContain("electron/loading.html");
            expect(docker, dockerfile).toContain("electron/crash.html");
            expect(docker, dockerfile).toContain("scripts/ensure-micron-parser-package.js");
        }
    });

    it("crash.html and loading.html apply theme in head before paint", () => {
        for (const rel of ["electron/crash.html", "electron/loading.html"]) {
            const html = readRepo(rel);
            expect(html, rel).toContain('name="color-scheme"');
            expect(html, rel).toContain("meshchatx_ui_theme");
            expect(html, rel).toContain('URLSearchParams(window.location.search).get("theme")');
            expect(html, rel).toContain('classList.add("dark")');
            expect(html, rel).toContain("background-color: #09090b");
            const headEnd = html.indexOf("</head>");
            const bootScript = html.indexOf("meshchatx_ui_theme");
            expect(bootScript, rel).toBeGreaterThan(-1);
            expect(bootScript, rel).toBeLessThan(headEnd);
        }
    });

    it("main process persists shell UI theme for file:// crash and loading pages", () => {
        const main = readRepo("electron/main.js");
        expect(main).toContain("getShellThemeQuery");
        expect(main).toContain("set-ui-theme");
        expect(main).toContain("shellBackgroundColor");
        expect(main).toContain("...getShellThemeQuery()");
        const preload = readRepo("electron/preload.js");
        expect(preload).toContain("setUiTheme");
        expect(preload).toContain("get-ui-theme");
    });

    it("compiled electron-shell.css includes utilities used by loading.html", () => {
        const css = readRepo("electron/assets/css/electron-shell.css");
        expect(css.length).toBeGreaterThan(1024);
        expect(css).toMatch(/\.min-h-screen|\.flex|\.rounded-2xl/);
        expect(css).toMatch(/\.dark\\:|@media \(prefers-color-scheme: dark\)/);
    });
});
