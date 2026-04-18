import { createRequire } from "module";
import path from "path";
import { fileURLToPath } from "url";
import { afterEach, describe, expect, it, vi } from "vitest";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const preloadPath = path.resolve(__dirname, "../../electron/preload.js");
const rootRequire = createRequire(import.meta.url);
const nodeModule = rootRequire("module");

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
    afterEach(() => {
        delete rootRequire.cache[preloadPath];
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
        expect(invoke).toHaveBeenCalledWith("show-notification", { title: "t", body: "b", silent: true });
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
