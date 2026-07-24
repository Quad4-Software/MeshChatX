// SPDX-License-Identifier: 0BSD

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

describe("apiClient CSRF recovery", () => {
    beforeEach(() => {
        vi.resetModules();
        global.window = { location: { origin: "http://127.0.0.1:5173" } };
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        vi.restoreAllMocks();
    });

    it("retries a mutating request once after refreshing a stale CSRF token", async () => {
        // Oracle: after a backgrounded web tab, the in-memory CSRF token can
        // disagree with the cookie session. A single 403 CSRF response must
        // refresh the token and retry, not treat the call as an auth logout.
        const { setCsrfToken, getCsrfToken } = await import("../../meshchatx/src/frontend/js/csrfToken.js");
        setCsrfToken("stale-token");

        const onAuthError = vi.fn();
        const { createApiClient } = await import("../../meshchatx/src/frontend/js/apiClient.js");
        const api = createApiClient({ onAuthError });

        let postCalls = 0;
        const fetchMock = vi.fn(async (url, init) => {
            const path = String(url);
            if (path.includes("/api/v1/auth/csrf") && (!init?.method || init.method === "GET")) {
                return {
                    ok: true,
                    status: 200,
                    headers: new Headers({ "content-type": "application/json" }),
                    text: async () => JSON.stringify({ csrf_token: "fresh-token" }),
                };
            }
            if (path.includes("/api/v1/destination/deadbeef/request-path") && init?.method === "POST") {
                postCalls += 1;
                const hdrs = init.headers instanceof Headers ? init.headers : new Headers(init.headers);
                const token = hdrs.get("X-CSRF-Token");
                if (token === "stale-token") {
                    return {
                        ok: false,
                        status: 403,
                        headers: new Headers({ "content-type": "application/json" }),
                        text: async () => JSON.stringify({ error: "Invalid or missing CSRF token" }),
                    };
                }
                if (token === "fresh-token") {
                    return {
                        ok: true,
                        status: 200,
                        headers: new Headers({ "content-type": "application/json" }),
                        text: async () => JSON.stringify({ message: "ok" }),
                    };
                }
            }
            return {
                ok: false,
                status: 500,
                headers: new Headers({ "content-type": "application/json" }),
                text: async () => JSON.stringify({ error: "unexpected" }),
            };
        });
        vi.stubGlobal("fetch", fetchMock);

        const result = await api.post("/api/v1/destination/deadbeef/request-path");

        expect(result.data).toEqual({ message: "ok" });
        expect(postCalls).toBe(2);
        expect(getCsrfToken()).toBe("fresh-token");
        expect(onAuthError).not.toHaveBeenCalled();
    });

    it("does not call onAuthError for CSRF 403 responses", async () => {
        const { setCsrfToken } = await import("../../meshchatx/src/frontend/js/csrfToken.js");
        setCsrfToken("stale-token");

        const onAuthError = vi.fn();
        const { createApiClient } = await import("../../meshchatx/src/frontend/js/apiClient.js");
        const api = createApiClient({ onAuthError });

        vi.stubGlobal("fetch", async () => ({
            ok: false,
            status: 403,
            headers: new Headers({ "content-type": "application/json" }),
            text: async () => JSON.stringify({ error: "Invalid or missing CSRF token" }),
        }));

        // Force refresh itself to fail so retry cannot succeed.
        await expect(api.post("/api/v1/destination/deadbeef/request-path")).rejects.toMatchObject({
            response: { status: 403 },
        });
        expect(onAuthError).not.toHaveBeenCalled();
    });

    it("still calls onAuthError for real auth 401 responses", async () => {
        const { setCsrfToken } = await import("../../meshchatx/src/frontend/js/csrfToken.js");
        setCsrfToken("good-token");

        const onAuthError = vi.fn();
        const { createApiClient } = await import("../../meshchatx/src/frontend/js/apiClient.js");
        const api = createApiClient({ onAuthError });

        vi.stubGlobal("fetch", async () => ({
            ok: false,
            status: 401,
            headers: new Headers({ "content-type": "application/json" }),
            text: async () => JSON.stringify({ error: "Authentication required" }),
        }));

        await expect(api.get("/api/v1/config")).rejects.toMatchObject({
            response: { status: 401 },
        });
        expect(onAuthError).toHaveBeenCalledTimes(1);
    });

    it("classifies CSRF rejection bodies without treating other 403s as CSRF", async () => {
        const { isCsrfRejection } = await import("../../meshchatx/src/frontend/js/apiClient.js");
        expect(isCsrfRejection(403, { error: "Invalid or missing CSRF token" })).toBe(true);
        expect(isCsrfRejection(403, { error: "Forbidden: client IP not on allowlist" })).toBe(false);
        expect(isCsrfRejection(401, { error: "Invalid or missing CSRF token" })).toBe(false);
        expect(isCsrfRejection(403, null)).toBe(false);
    });
});
