// SPDX-License-Identifier: 0BSD

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../../meshchatx/src/frontend/components/App.vue";

describe("App backend version-change reload", () => {
    let reloadFn;

    function makeCtx() {
        return {
            appInfo: null,
            bootVersionSignature: null,
            hasCheckedForModals: true,
            skipChangelogAfterTutorial: false,
            $refs: {},
            maybeShowAndroidStorageUpgrade: () => false,
            maybeShowPostInstallPrompt: async () => false,
            maybeShowChannelPrompt: () => false,
        };
    }

    function mockAppInfo(version, commit) {
        window.api = {
            get: vi.fn(async () => ({
                data: { app_info: { version, git_commit: commit } },
            })),
        };
    }

    beforeEach(() => {
        sessionStorage.clear();
        reloadFn = vi.fn();
        vi.stubGlobal("location", { ...window.location, reload: reloadFn });
        vi.spyOn(console, "log").mockImplementation(() => {});
    });

    afterEach(() => {
        delete window.api;
        vi.unstubAllGlobals();
        vi.restoreAllMocks();
    });

    it("records the boot signature on first info load without reloading", async () => {
        mockAppInfo("4.9.1", "abc123");
        const ctx = makeCtx();
        await App.methods.getAppInfo.call(ctx);
        expect(ctx.bootVersionSignature).toBe("4.9.1|abc123");
        expect(ctx.appInfo.version).toBe("4.9.1");
        expect(reloadFn).not.toHaveBeenCalled();
    });

    it("does not reload when the build signature is unchanged", async () => {
        mockAppInfo("4.9.1", "abc123");
        const ctx = makeCtx();
        await App.methods.getAppInfo.call(ctx);
        await App.methods.getAppInfo.call(ctx);
        expect(reloadFn).not.toHaveBeenCalled();
    });

    it("reloads once when the backend reports a different build", async () => {
        mockAppInfo("4.9.1", "abc123");
        const ctx = makeCtx();
        await App.methods.getAppInfo.call(ctx);
        window.api.get.mockResolvedValue({ data: { app_info: { version: "4.9.2", git_commit: "def456" } } });
        await App.methods.getAppInfo.call(ctx);
        expect(reloadFn).toHaveBeenCalledTimes(1);
        expect(sessionStorage.getItem("meshchatx.version_reload")).toBe("1");
    });

    it("does not reload-loop when the guard flag is already set", async () => {
        sessionStorage.setItem("meshchatx.version_reload", "1");
        mockAppInfo("4.9.1", "abc123");
        const ctx = makeCtx();
        await App.methods.getAppInfo.call(ctx);
        window.api.get.mockResolvedValue({ data: { app_info: { version: "4.9.2", git_commit: "def456" } } });
        await App.methods.getAppInfo.call(ctx);
        expect(reloadFn).not.toHaveBeenCalled();
    });

    it("tolerates a missing app_info payload without reloading", async () => {
        window.api = { get: vi.fn(async () => ({ data: {} })) };
        const ctx = makeCtx();
        await App.methods.getAppInfo.call(ctx);
        expect(ctx.bootVersionSignature).toBeNull();
        expect(reloadFn).not.toHaveBeenCalled();
    });
});
