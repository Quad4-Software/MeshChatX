// SPDX-License-Identifier: 0BSD

/**
 * Adversarial fuzzing and independent oracles for shell cache policy.
 */

import { describe, expect, it } from "vitest";
import {
    cacheNameForBuild,
    classifyShellRequest,
    isApiPath,
    shouldBypassCache,
} from "../../meshchatx/src/frontend/js/pwa/swCachePolicy.js";
import { oracleExpectedStrategy } from "../../meshchatx/src/frontend/js/pwa/swShellRuntime.js";

function mulberry32(seed) {
    let t = seed >>> 0;
    return () => {
        t += 0x6d2b79f5;
        let r = Math.imul(t ^ (t >>> 15), 1 | t);
        r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
        return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
    };
}

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

function assertClassifyMatchesOracle(request, url) {
    const actual = classifyShellRequest(request, url);
    const expected = oracleExpectedStrategy({
        method: request.method,
        pathname: url.pathname,
        mode: request.mode,
        destination: request.destination,
        accept: request.headers.get("accept") || "",
    });
    expect(actual).toBe(expected);
    if (expected === "bypass") {
        expect(shouldBypassCache(request, url)).toBe(true);
    }
    if (expected === "asset") {
        expect(url.pathname.startsWith("/assets")).toBe(true);
        expect(isApiPath(url.pathname)).toBe(false);
    }
    if (expected === "bypass" && (url.pathname.startsWith("/api") || url.pathname.startsWith("/ws"))) {
        expect(["bypass"]).toContain(actual);
    }
}

describe("swCachePolicy adversarial / oracle", () => {
    it("oracle: API and WS never classify as cacheable strategies", () => {
        for (const pathname of ["/api", "/api/v1/status", "/api/v1/auth/status", "/ws", "/ws/telephone/audio"]) {
            const url = new URL(`https://127.0.0.1${pathname}`);
            assertClassifyMatchesOracle(req(url.href), url);
            expect(classifyShellRequest(req(url.href), url)).toBe("bypass");
        }
    });

    it("oracle: mutating methods always bypass even for assets", () => {
        const url = new URL("https://127.0.0.1/assets/app.js");
        for (const method of ["POST", "PUT", "PATCH", "DELETE", "OPTIONS"]) {
            assertClassifyMatchesOracle(req(url.href, { method }), url);
            expect(classifyShellRequest(req(url.href, { method }), url)).toBe("bypass");
        }
    });

    it("oracle: path traversal-looking API prefixes still bypass", () => {
        for (const pathname of ["/api/../api/v1/status", "/api/%2e%2e/v1/status"]) {
            const url = new URL(`https://127.0.0.1${pathname}`);
            // URL parser normalizes ../ so /api/../api/v1/status -> /api/v1/status
            assertClassifyMatchesOracle(req(url.href), url);
        }
    });

    it("oracle: cache names never escape prefix and sanitize hostile build ids", () => {
        const hostile = ["../escape", "a/b", "x y", "v1;drop", "✨", ""];
        for (const buildId of hostile) {
            const name = cacheNameForBuild(buildId);
            expect(name.startsWith("meshchatx-shell-v")).toBe(true);
            expect(name).not.toContain("/");
            expect(name).not.toContain(" ");
            expect(name).not.toContain(";");
        }
    });

    it("fuzz: random path/method/mode inputs match independent oracle", () => {
        const rand = mulberry32(0xcace);
        const methods = ["GET", "HEAD", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"];
        const modes = ["cors", "navigate", "no-cors", "same-origin"];
        const destinations = ["", "document", "script", "style", "image", "worker"];
        const paths = [
            "/",
            "/index.html",
            "/assets/x.js",
            "/assets/vendor/a.css",
            "/boot-theme.js",
            "/manifest.json",
            "/favicons/favicon-512x512.png",
            "/favicon.ico",
            "/api/v1/status",
            "/api/v1/config",
            "/ws",
            "/ws/telephone/audio",
            "/service-worker.js",
            "/vendor/micron.wasm",
            "/meshchatx-docs/en/getting-started.md",
            "/#/messages",
            "//evil.example/assets/x.js",
            "/assets",
            "/api",
            "/API/v1/status",
            "/assets/../api/v1/status",
        ];
        for (let i = 0; i < 400; i++) {
            const pathname = paths[Math.floor(rand() * paths.length)];
            const method = methods[Math.floor(rand() * methods.length)];
            const mode = modes[Math.floor(rand() * modes.length)];
            const destination = destinations[Math.floor(rand() * destinations.length)];
            const accept = rand() > 0.7 ? "text/html" : "application/json";
            let url;
            try {
                url = new URL(pathname, "https://127.0.0.1");
            } catch {
                continue;
            }
            const request = req(url.href, {
                method,
                mode,
                destination,
                headers: { accept },
            });
            assertClassifyMatchesOracle(request, url);
        }
    });
});
