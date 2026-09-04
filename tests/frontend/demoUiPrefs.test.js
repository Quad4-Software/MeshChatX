// SPDX-License-Identifier: 0BSD

import { beforeEach, describe, expect, it, vi } from "vitest";
import {
    DEMO_UI_PREFS_STORAGE_KEY,
    isDemoReadonlyRejection,
    loadDemoUiPrefs,
    mergeAndSaveDemoUiPrefs,
    mergeConfigWithDemoUiPrefs,
    partialHasDemoUiPrefs,
    pickDemoUiPrefs,
} from "../../meshchatx/src/frontend/js/demoUiPrefs.js";
import { createApiClient } from "../../meshchatx/src/frontend/js/apiClient.js";
import GlobalState from "../../meshchatx/src/frontend/js/GlobalState.js";

function memoryStorage() {
    /** @type {Record<string, string>} */
    const map = {};
    return {
        getItem(key) {
            return Object.prototype.hasOwnProperty.call(map, key) ? map[key] : null;
        },
        setItem(key, value) {
            map[key] = String(value);
        },
        removeItem(key) {
            delete map[key];
        },
    };
}

describe("demoUiPrefs", () => {
    it("picks only allowlisted UI keys", () => {
        expect(
            pickDemoUiPrefs({
                theme: "dark",
                language: "de",
                privacy_mode_enabled: false,
                display_name: "Demo",
            })
        ).toEqual({
            theme: "dark",
            language: "de",
            display_name: "Demo",
        });
    });

    it("merges and reloads prefs from storage", () => {
        const storage = memoryStorage();
        mergeAndSaveDemoUiPrefs({ theme: "dark", language: "fr" }, storage);
        expect(loadDemoUiPrefs(storage)).toEqual({ theme: "dark", language: "fr" });
        expect(storage.getItem(DEMO_UI_PREFS_STORAGE_KEY)).toContain("dark");
        expect(mergeConfigWithDemoUiPrefs({ theme: "light", display_name: "Server" }, storage)).toEqual({
            theme: "dark",
            display_name: "Server",
            language: "fr",
        });
    });

    it("detects demo_readonly rejections", () => {
        expect(isDemoReadonlyRejection({ code: "demo_readonly" })).toBe(true);
        expect(isDemoReadonlyRejection({ code: "other" })).toBe(false);
        expect(partialHasDemoUiPrefs({ theme: "dark" })).toBe(true);
        expect(partialHasDemoUiPrefs({ privacy_mode_enabled: true })).toBe(false);
    });
});

describe("apiClient demo config overlay", () => {
    beforeEach(() => {
        GlobalState.demoMode = true;
        GlobalState.config = { theme: "light", display_name: "Server" };
        vi.stubGlobal("localStorage", memoryStorage());
        vi.stubGlobal(
            "fetch",
            vi.fn(async () => {
                throw new Error("network should not be used for demo UI prefs");
            })
        );
    });

    it("stores theme and language patches locally in demo mode", async () => {
        const api = createApiClient();
        const response = await api.patch("/api/v1/config", { theme: "dark", language: "es" });
        expect(response.status).toBe(200);
        expect(response.data.config.theme).toBe("dark");
        expect(response.data.config.language).toBe("es");
        expect(fetch).not.toHaveBeenCalled();
    });

    it("merges stored prefs into GET /api/v1/config in demo mode", async () => {
        mergeAndSaveDemoUiPrefs({ theme: "dark", language: "nl" });
        vi.stubGlobal(
            "fetch",
            vi.fn(async () => ({
                ok: true,
                status: 200,
                headers: new Headers({ "content-type": "application/json" }),
                text: async () =>
                    JSON.stringify({
                        config: { theme: "light", display_name: "Server", language: "en" },
                    }),
            }))
        );
        const api = createApiClient();
        const response = await api.get("/api/v1/config");
        expect(response.data.config.theme).toBe("dark");
        expect(response.data.config.language).toBe("nl");
        expect(response.data.config.display_name).toBe("Server");
    });

    it("does not treat demo_readonly as an auth error", async () => {
        GlobalState.demoMode = true;
        const onAuthError = vi.fn();
        vi.stubGlobal(
            "fetch",
            vi.fn(async () => ({
                ok: false,
                status: 403,
                headers: new Headers({ "content-type": "application/json" }),
                text: async () => JSON.stringify({ error: "Demo mode is read-only", code: "demo_readonly" }),
            }))
        );
        const api = createApiClient({ onAuthError });
        await expect(api.patch("/api/v1/config", { privacy_mode_enabled: false })).rejects.toMatchObject({
            response: { status: 403 },
        });
        expect(onAuthError).not.toHaveBeenCalled();
    });
});
