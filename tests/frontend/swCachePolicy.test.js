// SPDX-License-Identifier: 0BSD

import { describe, it, expect } from "vitest";
import {
    SHELL_CACHE_PREFIX,
    cacheNameForBuild,
    isApiPath,
    isHashedAssetPath,
    isShellHelperPath,
    isNavigationRequest,
    shouldBypassCache,
    classifyShellRequest,
} from "../../meshchatx/src/frontend/js/pwa/swCachePolicy.js";

function req(url, init = {}) {
    const headers = new Headers(init.headers || {});
    return {
        url,
        method: init.method || "GET",
        mode: init.mode || "cors",
        destination: init.destination || "",
        headers,
    };
}

describe("swCachePolicy", () => {
    it("builds versioned cache names", () => {
        expect(cacheNameForBuild("2026-07-24T12:00:00.000Z")).toBe(`${SHELL_CACHE_PREFIX}v2026-07-24T12_00_00.000Z`);
        expect(cacheNameForBuild("")).toBe(`${SHELL_CACHE_PREFIX}vdev`);
    });

    it("detects API and asset paths", () => {
        expect(isApiPath("/api")).toBe(true);
        expect(isApiPath("/api/v1/status")).toBe(true);
        expect(isApiPath("/assets/index.js")).toBe(false);
        expect(isHashedAssetPath("/assets/app-abc.js")).toBe(true);
        expect(isHashedAssetPath("/assets")).toBe(true);
        expect(isHashedAssetPath("/boot-theme.js")).toBe(false);
    });

    it("detects shell helper paths", () => {
        expect(isShellHelperPath("/boot-theme.js")).toBe(true);
        expect(isShellHelperPath("/manifest.json")).toBe(true);
        expect(isShellHelperPath("/favicons/favicon-512x512.png")).toBe(true);
        expect(isShellHelperPath("/api/v1/status")).toBe(false);
    });

    it("detects navigation requests", () => {
        expect(isNavigationRequest(req("https://127.0.0.1/", { mode: "navigate" }))).toBe(true);
        expect(isNavigationRequest(req("https://127.0.0.1/", { destination: "document" }))).toBe(true);
        expect(
            isNavigationRequest(
                req("https://127.0.0.1/", {
                    headers: { accept: "text/html,application/xhtml+xml" },
                })
            )
        ).toBe(true);
        expect(isNavigationRequest(req("https://127.0.0.1/assets/x.js"))).toBe(false);
    });

    it("bypasses non-GET, API, ws, and service worker script", () => {
        const apiUrl = new URL("https://127.0.0.1/api/v1/status");
        expect(shouldBypassCache(req(apiUrl.href, { method: "POST" }), apiUrl)).toBe(true);
        expect(shouldBypassCache(req(apiUrl.href), apiUrl)).toBe(true);
        const wsUrl = new URL("https://127.0.0.1/ws");
        expect(shouldBypassCache(req(wsUrl.href), wsUrl)).toBe(true);
        const swUrl = new URL("https://127.0.0.1/service-worker.js");
        expect(shouldBypassCache(req(swUrl.href), swUrl)).toBe(true);
        const assetUrl = new URL("https://127.0.0.1/assets/a.js");
        expect(shouldBypassCache(req(assetUrl.href), assetUrl)).toBe(false);
    });

    it("classifies requests for shell strategies", () => {
        const assetUrl = new URL("https://127.0.0.1/assets/chunk.js");
        expect(classifyShellRequest(req(assetUrl.href), assetUrl)).toBe("asset");

        const navUrl = new URL("https://127.0.0.1/");
        expect(classifyShellRequest(req(navUrl.href, { mode: "navigate" }), navUrl)).toBe("navigation");

        const helperUrl = new URL("https://127.0.0.1/boot-theme.js");
        expect(classifyShellRequest(req(helperUrl.href), helperUrl)).toBe("shell-helper");

        const apiUrl = new URL("https://127.0.0.1/api/v1/config");
        expect(classifyShellRequest(req(apiUrl.href), apiUrl)).toBe("bypass");

        const otherUrl = new URL("https://127.0.0.1/vendor/x.wasm");
        expect(classifyShellRequest(req(otherUrl.href), otherUrl)).toBe("network-only");
    });
});
