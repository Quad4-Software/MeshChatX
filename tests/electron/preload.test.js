import { createRequire } from "module";
import path from "path";
import { fileURLToPath } from "url";
import { afterEach, describe, expect, it, vi } from "vitest";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const preloadPath = path.resolve(__dirname, "../../electron/preload.js");
const rootRequire = createRequire(import.meta.url);
const nodeModule = rootRequire("module");

const TRUSTED_SHELL_HREF = "https://127.0.0.1:9337/#/messages";

function loadPreloadWithElectronMock(mockElectron) {
    const orig = nodeModule.prototype.require;
    nodeModule.prototype.require = function patchedRequire(id) {
        if (id === "electron") {
            return mockElectron;
        }
        return orig.apply(this, arguments);
    };
    try {
        delete rootRequire.cache[preloadPath];
        rootRequire(preloadPath);
    } finally {
        nodeModule.prototype.require = orig;
    }
}

describe("electron/preload", () => {
    let previousLocation;

    beforeEach(() => {
        previousLocation = globalThis.location;
        globalThis.location = { href: TRUSTED_SHELL_HREF };
    });

    afterEach(() => {
        delete rootRequire.cache[preloadPath];
        if (previousLocation === undefined) {
            delete globalThis.location;
        } else {
            globalThis.location = previousLocation;
        }
    });

    it("registers contextBridge API and forwards invoke to ipcRenderer", async () => {
        const exposeInMainWorld = vi.fn();
        const invoke = vi.fn();
        const on = vi.fn();
        const mockElectron = {
            contextBridge: { exposeInMainWorld },
            ipcRenderer: { invoke, on },
        };
        loadPreloadWithElectronMock(mockElectron);
        expect(exposeInMainWorld).toHaveBeenCalledWith("electron", expect.any(Object));
        const api = exposeInMainWorld.mock.calls[0][1];
        invoke.mockResolvedValueOnce("9.9.9");
        await expect(api.appVersion()).resolves.toBe("9.9.9");
        expect(invoke).toHaveBeenCalledWith("app-version");

        invoke.mockResolvedValueOnce(true);
        await expect(api.isHardwareAccelerationEnabled()).resolves.toBe(true);
        expect(invoke).toHaveBeenCalledWith("is-hardware-acceleration-enabled");

        api.showNotification("t", "b", true);
        expect(invoke).toHaveBeenCalledWith("show-notification", {
            title: "t",
            body: "b",
            silent: true,
            destinationHash: null,
        });
        api.showNotification("t2", "b2", false, "peerhash");
        expect(invoke).toHaveBeenCalledWith("show-notification", {
            title: "t2",
            body: "b2",
            silent: false,
            destinationHash: "peerhash",
        });
        api.closeMessageNotifications("abcd");
        expect(invoke).toHaveBeenCalledWith("close-message-notifications", "abcd");
        api.closeMessageNotifications();
        expect(invoke).toHaveBeenCalledWith("close-message-notifications", null);
    });

    it("onProtocolLink registers ipc listener for open-protocol-link", () => {
        const exposeInMainWorld = vi.fn();
        const invoke = vi.fn();
        const on = vi.fn();
        loadPreloadWithElectronMock({
            contextBridge: { exposeInMainWorld },
            ipcRenderer: { invoke, on },
        });
        const api = exposeInMainWorld.mock.calls[0][1];
        const cb = vi.fn();
        api.onProtocolLink(cb);
        const handler = on.mock.calls.find((c) => c[0] === "open-protocol-link")?.[1];
        expect(handler).toEqual(expect.any(Function));
        handler({}, "rns://x");
        expect(cb).toHaveBeenCalledWith("rns://x");
    });

    it("exposes backend recovery IPC helpers", async () => {
        const exposeInMainWorld = vi.fn();
        const invoke = vi.fn();
        const on = vi.fn();
        loadPreloadWithElectronMock({
            contextBridge: { exposeInMainWorld },
            ipcRenderer: { invoke, on },
        });
        const api = exposeInMainWorld.mock.calls[0][1];
        invoke.mockResolvedValueOnce({ ok: true });
        await expect(api.restartBackend()).resolves.toEqual({ ok: true });
        expect(invoke).toHaveBeenCalledWith("restart-backend");

        const cb = vi.fn();
        api.onBackendProcessExited(cb);
        const handler = on.mock.calls.find((c) => c[0] === "backend-process-exited")?.[1];
        handler({}, { code: 255 });
        expect(cb).toHaveBeenCalledWith({ code: 255 });
    });

    it("exposes close settings IPC helpers", async () => {
        const exposeInMainWorld = vi.fn();
        const invoke = vi.fn();
        loadPreloadWithElectronMock({
            contextBridge: { exposeInMainWorld },
            ipcRenderer: { invoke, on: vi.fn() },
        });
        const api = exposeInMainWorld.mock.calls[0][1];
        invoke.mockResolvedValueOnce({ closeBehavior: "ask", trayEnabled: true });
        await expect(api.getCloseSettings()).resolves.toEqual({ closeBehavior: "ask", trayEnabled: true });
        expect(invoke).toHaveBeenCalledWith("get-close-settings");

        invoke.mockResolvedValueOnce({ closeBehavior: "quit", trayEnabled: false });
        await expect(api.setCloseSettings({ closeBehavior: "quit" })).resolves.toEqual({
            closeBehavior: "quit",
            trayEnabled: false,
        });
        expect(invoke).toHaveBeenCalledWith("set-close-settings", { closeBehavior: "quit" });
    });

    it("exposes UI theme IPC helpers for shell pages", async () => {
        const exposeInMainWorld = vi.fn();
        const invoke = vi.fn();
        loadPreloadWithElectronMock({
            contextBridge: { exposeInMainWorld },
            ipcRenderer: { invoke, on: vi.fn() },
        });
        const api = exposeInMainWorld.mock.calls[0][1];
        invoke.mockResolvedValueOnce({ preference: "dark", theme: "dark" });
        await expect(api.getUiTheme()).resolves.toEqual({ preference: "dark", theme: "dark" });
        expect(invoke).toHaveBeenCalledWith("get-ui-theme");

        invoke.mockResolvedValueOnce({ preference: "dark", theme: "dark" });
        await expect(api.setUiTheme("dark")).resolves.toEqual({ preference: "dark", theme: "dark" });
        expect(invoke).toHaveBeenCalledWith("set-ui-theme", "dark");
    });

    it("exposes screen security IPC helpers and platform", async () => {
        const exposeInMainWorld = vi.fn();
        const invoke = vi.fn();
        loadPreloadWithElectronMock({
            contextBridge: { exposeInMainWorld },
            ipcRenderer: { invoke, on: vi.fn() },
        });
        const api = exposeInMainWorld.mock.calls[0][1];
        expect(typeof api.getPlatform).toBe("function");

        invoke.mockResolvedValueOnce({
            platform: "win32",
            available: true,
            windowsDrm: true,
            enabled: false,
        });
        await expect(api.getScreenSecuritySettings()).resolves.toEqual({
            platform: "win32",
            available: true,
            windowsDrm: true,
            enabled: false,
        });
        expect(invoke).toHaveBeenCalledWith("get-screen-security-settings");

        invoke.mockResolvedValueOnce({
            platform: "win32",
            available: true,
            windowsDrm: true,
            enabled: true,
        });
        await expect(api.setScreenSecurityEnabled(true)).resolves.toEqual({
            platform: "win32",
            available: true,
            windowsDrm: true,
            enabled: true,
        });
        expect(invoke).toHaveBeenCalledWith("set-screen-security-enabled", true);
    });

    it("subscribes to log channel on load", () => {
        const exposeInMainWorld = vi.fn();
        const on = vi.fn();
        loadPreloadWithElectronMock({
            contextBridge: { exposeInMainWorld },
            ipcRenderer: { invoke: vi.fn(), on },
        });
        expect(on).toHaveBeenCalledWith("log", expect.any(Function));
    });
});
