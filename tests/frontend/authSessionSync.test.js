// SPDX-License-Identifier: 0BSD

import { readFileSync, existsSync } from "fs";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import GlobalState from "../../meshchatx/src/frontend/js/GlobalState.js";
import {
    AUTH_STATUS_TIMEOUT_MS,
    applyAuthStatusToGlobalState,
    authNavigationTargetForStatus,
    fetchAuthStatus,
    resolveAuthNavigation,
} from "../../meshchatx/src/frontend/js/authSessionSync.js";

describe("authSessionSync", () => {
    beforeEach(() => {
        GlobalState.authSessionResolved = false;
        GlobalState.authEnabled = false;
        GlobalState.authenticated = false;
        GlobalState.demoMode = false;
        GlobalState.isLoopbackBind = true;
    });

    afterEach(() => {
        vi.useRealTimers();
        vi.restoreAllMocks();
    });

    it("applies auth status into GlobalState", () => {
        applyAuthStatusToGlobalState({
            auth_enabled: true,
            authenticated: true,
            demo_mode: true,
            is_loopback_bind: false,
        });
        expect(GlobalState.authEnabled).toBe(true);
        expect(GlobalState.authenticated).toBe(true);
        expect(GlobalState.demoMode).toBe(true);
        expect(GlobalState.isLoopbackBind).toBe(false);
        expect(GlobalState.authSessionResolved).toBe(true);
    });

    it("routes authenticated users away from auth", () => {
        const target = authNavigationTargetForStatus({ name: "auth" }, { auth_enabled: true, authenticated: true });
        expect(target).toEqual({ redirect: "/" });
    });

    it("routes unauthenticated users to auth", () => {
        const target = authNavigationTargetForStatus(
            { name: "messages" },
            { auth_enabled: true, authenticated: false }
        );
        expect(target).toEqual({ redirect: "/auth" });
    });

    it("aborts auth status fetch after timeout so navigation guards cannot hang", async () => {
        vi.useFakeTimers();
        const api = {
            get: vi.fn((_path, config) => {
                return new Promise((resolve, reject) => {
                    if (config?.signal?.aborted) {
                        reject(new DOMException("Aborted", "AbortError"));
                        return;
                    }
                    config?.signal?.addEventListener("abort", () => {
                        reject(new DOMException("Aborted", "AbortError"));
                    });
                });
            }),
        };

        const pending = fetchAuthStatus(api);
        const assertion = expect(pending).rejects.toMatchObject({ name: "AbortError" });
        await vi.advanceTimersByTimeAsync(AUTH_STATUS_TIMEOUT_MS + 1);
        await assertion;
        expect(api.get).toHaveBeenCalledTimes(1);
    });

    it("allows navigation when auth status fetch times out during backend outage", async () => {
        vi.useFakeTimers();
        const api = {
            get: vi.fn((_path, config) => {
                return new Promise((resolve, reject) => {
                    if (config?.signal?.aborted) {
                        reject(new DOMException("Aborted", "AbortError"));
                        return;
                    }
                    config?.signal?.addEventListener("abort", () => {
                        reject(new DOMException("Aborted", "AbortError"));
                    });
                });
            }),
        };

        const pending = resolveAuthNavigation({ name: "messages" }, api);
        await vi.advanceTimersByTimeAsync(AUTH_STATUS_TIMEOUT_MS + 1);
        const decision = await pending;
        expect(decision).toEqual({ allow: true });
        expect(GlobalState.authSessionResolved).toBe(true);
    });
});

describe("auth boot defaults", () => {
    it("keeps authSessionResolved false until status is applied", () => {
        const filePath = existsSync("meshchatx/src/frontend/js/GlobalState.ts")
            ? "meshchatx/src/frontend/js/GlobalState.ts"
            : "meshchatx/src/frontend/js/GlobalState.js";
        const src = readFileSync(filePath, "utf8");
        expect(src).toMatch(/authSessionResolved:\s*false/);
    });
});
