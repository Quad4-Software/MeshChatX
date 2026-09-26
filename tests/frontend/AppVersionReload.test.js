// SPDX-License-Identifier: 0BSD

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getAppInfo } from "@/features/app-shell/lib/appShellConfig.ts";

describe("App backend version-change reload", () => {
    let reloadFn;

    function makeState() {
        return {
            appInfo: null,
            bootVersionSignature: null,
            hasCheckedForModals: true,
            skipChangelogAfterTutorial: false,
            hosts: {},
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
        Object.defineProperty(window, "location", {
            value: { ...window.location, reload: reloadFn },
            writable: true,
        });
        vi.spyOn(console, "log").mockImplementation(() => {});
    });

    afterEach(() => {
        delete window.api;
        vi.restoreAllMocks();
    });

    it("records the boot signature on first info load without reloading", async () => {
        mockAppInfo("4.9.1", "abc123");
        const state = makeState();
        await getAppInfo(state);
        expect(state.bootVersionSignature).toBe("4.9.1|abc123");
        expect(state.appInfo.version).toBe("4.9.1");
        expect(reloadFn).not.toHaveBeenCalled();
    });

    it("does not reload when the build signature is unchanged", async () => {
        mockAppInfo("4.9.1", "abc123");
        const state = makeState();
        await getAppInfo(state);
        await getAppInfo(state);
        expect(reloadFn).not.toHaveBeenCalled();
    });

    it("reloads once when the backend reports a different build", async () => {
        mockAppInfo("4.9.1", "abc123");
        const state = makeState();
        await getAppInfo(state);
        window.api.get.mockResolvedValue({ data: { app_info: { version: "4.9.2", git_commit: "def456" } } });
        await getAppInfo(state);
        expect(reloadFn).toHaveBeenCalledTimes(1);
        expect(sessionStorage.getItem("meshchatx.version_reload")).toBe("1");
    });

    it("does not reload-loop when the guard flag is already set", async () => {
        sessionStorage.setItem("meshchatx.version_reload", "1");
        mockAppInfo("4.9.1", "abc123");
        const state = makeState();
        await getAppInfo(state);
        window.api.get.mockResolvedValue({ data: { app_info: { version: "4.9.2", git_commit: "def456" } } });
        await getAppInfo(state);
        expect(reloadFn).not.toHaveBeenCalled();
        expect(state.appInfo.version).toBe("4.9.2");
    });
});
