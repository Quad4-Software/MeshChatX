// SPDX-License-Identifier: 0BSD

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = resolve(import.meta.dirname, "../..");

function readRepo(relPath) {
    return readFileSync(resolve(ROOT, relPath), "utf8");
}

describe("electron packaging and security oracle", () => {
    it("electron-builder fuses harden the packaged binary", () => {
        const pkg = JSON.parse(readRepo("package.json"));
        const fuses = pkg.build.electronFuses;
        expect(fuses.runAsNode).toBe(false);
        expect(fuses.enableNodeOptionsEnvironmentVariable).toBe(false);
        expect(fuses.enableNodeCliInspectArguments).toBe(false);
        expect(fuses.enableCookieEncryption).toBe(true);
        expect(fuses.enableEmbeddedAsarIntegrityValidation).toBe(true);
        expect(fuses.onlyLoadAppFromAsar).toBe(true);
    });

    it("main BrowserWindow uses sandbox, context isolation, and no nodeIntegration", () => {
        const main = readRepo("electron/main.js");
        expect(main).toContain("nodeIntegration: false");
        expect(main).toContain("contextIsolation: true");
        expect(main).toContain("sandbox: true");
        expect(main).toContain("enableRemoteModule: false");
    });

    it("child popout windows inherit the same webPreferences hardening", () => {
        const main = readRepo("electron/main.js");
        expect(main).toContain("function getChildBrowserWindowOptions");
        expect(main).toContain("overrideBrowserWindowOptions: getChildBrowserWindowOptions()");
    });

    it("registers navigation and window-open guards on every web contents", () => {
        const main = readRepo("electron/main.js");
        expect(main).toContain('app.on("web-contents-created"');
        expect(main).toContain("attachWindowOpenHandler(contents)");
        expect(main).toContain("attachInWindowNavigationGuard(contents)");
        expect(main).toContain('webContents.on("will-attach-webview"');
    });

    it("session applies CSP fallback and MeshChatX-owned download path", () => {
        const main = readRepo("electron/main.js");
        expect(main).toContain("webRequest.onHeadersReceived");
        expect(main).toContain("Content-Security-Policy");
        expect(main).toContain("setDownloadPath");
        expect(main).toContain('"MeshChatX"');
    });

    it("hardware permissions use explicit allowlists with user prompts for devices", () => {
        const hw = readRepo("electron/hardwareDevicePermissions.js");
        expect(hw).toContain("setPermissionCheckHandler");
        expect(hw).toContain("setPermissionRequestHandler");
        expect(hw).toContain('"select-serial-port"');
        expect(hw).toContain('"select-usb-device"');
    });

    it("preload exposes a bounded IPC surface via contextBridge", () => {
        const preload = readRepo("electron/preload.js");
        expect(preload).toContain("contextBridge.exposeInMainWorld");
        expect(preload).not.toContain('exposeInMainWorld("ipcRenderer"');
        expect(preload).toContain("isTrustedShellOrigin");
    });

    it("does not load remote code in the main window (local loading.html bootstrap)", () => {
        const main = readRepo("electron/main.js");
        expect(main).toContain("loadFile");
        expect(main).toContain("loading.html");
        expect(main).not.toContain('loadURL("http');
        expect(main).not.toContain("loadURL('http");
    });
});
