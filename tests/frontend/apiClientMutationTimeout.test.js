// SPDX-License-Identifier: 0BSD

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

describe("apiClient mutation timeout", () => {
    beforeEach(() => {
        vi.resetModules();
        global.window = { location: { origin: "http://127.0.0.1:5173" } };
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        vi.restoreAllMocks();
        vi.useRealTimers();
    });

    it("rejects a stuck POST with TimeoutError without aborting the fetch", async () => {
        // Oracle: a mutation fired just before the WebView freezes can sit
        // pending forever. The caller must be released, but the underlying
        // request is left alone because the server may still be processing it.
        const { setCsrfToken } = await import("../../meshchatx/src/frontend/js/csrfToken.js");
        setCsrfToken("tok");
        const { createApiClient } = await import("../../meshchatx/src/frontend/js/apiClient.js");
        const api = createApiClient();

        let capturedInit;
        vi.stubGlobal("fetch", (url, init) => {
            capturedInit = init;
            return new Promise(() => {});
        });

        vi.useFakeTimers();
        const promise = api.post("/api/v1/config", { a: 1 }, { timeout: 50 });
        const assertion = expect(promise).rejects.toMatchObject({
            name: "TimeoutError",
            message: "Request timed out after 50ms",
        });
        await vi.advanceTimersByTimeAsync(60);
        await assertion;
        expect(capturedInit.signal).toBeUndefined();
    });

    it("applies the default mutation timeout to POST", async () => {
        const { setCsrfToken } = await import("../../meshchatx/src/frontend/js/csrfToken.js");
        setCsrfToken("tok");
        const { createApiClient } = await import("../../meshchatx/src/frontend/js/apiClient.js");
        const api = createApiClient();

        vi.stubGlobal("fetch", () => new Promise(() => {}));

        vi.useFakeTimers();
        const promise = api.post("/api/v1/config", { a: 1 });
        const assertion = expect(promise).rejects.toMatchObject({ name: "TimeoutError" });
        await vi.advanceTimersByTimeAsync(120001);
        await assertion;
    });

    it("does not apply the mutation timeout to GET requests", async () => {
        const { createApiClient } = await import("../../meshchatx/src/frontend/js/apiClient.js");
        const api = createApiClient();

        vi.stubGlobal("fetch", () => new Promise(() => {}));

        vi.useFakeTimers();
        const promise = api.get("/api/v1/config");
        let settled = false;
        promise.then(
            () => (settled = true),
            () => (settled = true)
        );
        await vi.advanceTimersByTimeAsync(130000);
        expect(settled).toBe(false);
    });
});
