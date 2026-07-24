// SPDX-License-Identifier: 0BSD

/**
 * Runtime strategy oracles: races, leaks, update prune, navigation timeout fallback.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { cacheNameForBuild, SHELL_CACHE_PREFIX } from "../../meshchatx/src/frontend/js/pwa/swCachePolicy.js";
import {
    createShellRuntime,
    findForbiddenCachedUrls,
    oracleExpectedStrategy,
    selectCachesToDelete,
    SHELL_FALLBACK_URL,
} from "../../meshchatx/src/frontend/js/pwa/swShellRuntime.js";
import {
    decideControllerChangeReload,
    isIgnorableServiceWorkerRegistrationError,
    serviceWorkerRegisterOptions,
} from "../../meshchatx/src/frontend/js/pwa/swClientRegister.js";
import { makeRequest, MemoryCacheStorage, okResponse } from "./helpers/memoryCacheStorage.js";

const ORIGIN = "https://127.0.0.1:8000";

function assertNoApiLeakOracle(cacheStorage) {
    const leaked = findForbiddenCachedUrls(cacheStorage.allUrls());
    expect(leaked).toEqual([]);
}

describe("swShellRuntime oracle / race / leak", () => {
    afterEach(() => {
        vi.useRealTimers();
    });

    it("oracle: cache-first serves cached asset and never stores API", async () => {
        const caches = new MemoryCacheStorage();
        const cacheName = cacheNameForBuild("t1");
        const assetUrl = `${ORIGIN}/assets/app-abc.js`;
        let fetches = 0;
        const fetchFn = vi.fn(async (request) => {
            fetches += 1;
            const url = typeof request === "string" ? request : request.url;
            if (url.includes("/api/")) {
                return okResponse('{"secret":true}', { headers: { "content-type": "application/json" } });
            }
            return okResponse("asset-v1");
        });
        const runtime = createShellRuntime({
            caches,
            fetch: fetchFn,
            cacheName,
            origin: ORIGIN,
        });

        const assetReq = makeRequest(assetUrl);
        const first = await runtime.cacheFirst(assetReq);
        expect(await first.text()).toBe("asset-v1");
        const second = await runtime.cacheFirst(assetReq);
        expect(await second.text()).toBe("asset-v1");
        expect(fetches).toBe(1);

        const apiReq = makeRequest(`${ORIGIN}/api/v1/status`);
        expect(runtime.resolveFetch(apiReq)).toBeNull();
        expect(oracleExpectedStrategy({ pathname: "/api/v1/status", method: "GET" })).toBe("bypass");
        assertNoApiLeakOracle(caches);
    });

    it("oracle: failed network responses are not written to cache", async () => {
        const caches = new MemoryCacheStorage();
        const cacheName = cacheNameForBuild("t2");
        const assetUrl = `${ORIGIN}/assets/missing.js`;
        const fetchFn = vi.fn(async () => new Response("nope", { status: 404 }));
        const runtime = createShellRuntime({ caches, fetch: fetchFn, cacheName, origin: ORIGIN });
        const response = await runtime.cacheFirst(makeRequest(assetUrl));
        expect(response.status).toBe(404);
        expect(caches.allUrls()).toEqual([]);
    });

    it("race: concurrent cache-first misses do not leak and stabilize on one body", async () => {
        const caches = new MemoryCacheStorage();
        const cacheName = cacheNameForBuild("race");
        const assetUrl = `${ORIGIN}/assets/race.js`;
        let started = 0;
        let release;
        const gate = new Promise((resolve) => {
            release = resolve;
        });
        const fetchFn = vi.fn(async () => {
            started += 1;
            await gate;
            return okResponse(`body-${started}`);
        });
        const runtime = createShellRuntime({ caches, fetch: fetchFn, cacheName, origin: ORIGIN });
        const req = makeRequest(assetUrl);
        const p1 = runtime.cacheFirst(req);
        const p2 = runtime.cacheFirst(req);
        await vi.waitFor(() => {
            expect(started).toBe(2);
        });
        release();
        const [r1, r2] = await Promise.all([p1, p2]);
        const t1 = await r1.text();
        const t2 = await r2.text();
        expect(t1.startsWith("body-")).toBe(true);
        expect(t2.startsWith("body-")).toBe(true);
        assertNoApiLeakOracle(caches);
        const cached = await caches.match(req);
        expect(cached).toBeTruthy();
        expect((await cached.text()).startsWith("body-")).toBe(true);
    });

    it("race: prune deletes only old shell caches and keeps current", async () => {
        const caches = new MemoryCacheStorage();
        const oldName = cacheNameForBuild("old");
        const newName = cacheNameForBuild("new");
        const oldCache = await caches.open(oldName);
        const newCache = await caches.open(newName);
        await oldCache.put(`${ORIGIN}/assets/old.js`, okResponse("old"));
        await newCache.put(`${ORIGIN}/assets/new.js`, okResponse("new"));
        await caches.open("unrelated-other");

        const doomed = selectCachesToDelete(await caches.keys(), SHELL_CACHE_PREFIX, newName);
        expect(doomed).toEqual([oldName]);

        const runtime = createShellRuntime({
            caches,
            fetch: vi.fn(),
            cacheName: newName,
            origin: ORIGIN,
        });
        const deleted = await runtime.pruneOldShellCaches();
        expect(deleted).toEqual([oldName]);
        expect(await caches.keys()).toEqual(expect.arrayContaining([newName, "unrelated-other"]));
        expect(await caches.keys()).not.toContain(oldName);
        expect(await (await caches.open(newName)).match(`${ORIGIN}/assets/new.js`)).toBeTruthy();
    });

    it("edge: navigation timeout falls back to cached shell without caching API", async () => {
        vi.useFakeTimers();
        const caches = new MemoryCacheStorage();
        const cacheName = cacheNameForBuild("nav");
        const shell = okResponse("<html>shell</html>", { headers: { "content-type": "text/html" } });
        await (await caches.open(cacheName)).put(SHELL_FALLBACK_URL, shell);

        const fetchFn = vi.fn((_request, init = {}) => {
            return new Promise((resolve, reject) => {
                if (init.signal) {
                    init.signal.addEventListener("abort", () => {
                        reject(new DOMException("Aborted", "AbortError"));
                    });
                }
            });
        });
        const runtime = createShellRuntime({
            caches,
            fetch: fetchFn,
            cacheName,
            origin: ORIGIN,
            navTimeoutMs: 50,
        });
        const navReq = makeRequest(`${ORIGIN}/`, { mode: "navigate" });
        const pending = runtime.networkFirstNavigation({ request: navReq });
        await vi.advanceTimersByTimeAsync(60);
        const response = await pending;
        expect(await response.text()).toContain("shell");
        assertNoApiLeakOracle(caches);
    });

    it("edge: cross-origin and network-only paths bypass respondWith", () => {
        const caches = new MemoryCacheStorage();
        const runtime = createShellRuntime({
            caches,
            fetch: vi.fn(),
            cacheName: cacheNameForBuild("x"),
            origin: ORIGIN,
        });
        expect(runtime.resolveFetch(makeRequest("https://evil.example/assets/x.js"))).toBeNull();
        expect(runtime.resolveFetch(makeRequest(`${ORIGIN}/vendor/x.wasm`))).toBeNull();
        expect(runtime.resolveFetch(makeRequest(`${ORIGIN}/api/v1/status`))).toBeNull();
        expect(runtime.resolveFetch(makeRequest(`${ORIGIN}/ws`))).toBeNull();
    });

    it("edge: stale-while-revalidate returns cache immediately then refreshes", async () => {
        const caches = new MemoryCacheStorage();
        const cacheName = cacheNameForBuild("swr");
        const url = `${ORIGIN}/boot-theme.js`;
        await (await caches.open(cacheName)).put(url, okResponse("old-theme"));
        let resolveNet;
        const net = new Promise((resolve) => {
            resolveNet = resolve;
        });
        const fetchFn = vi.fn(() => net);
        const runtime = createShellRuntime({ caches, fetch: fetchFn, cacheName, origin: ORIGIN });
        const first = await runtime.staleWhileRevalidate(makeRequest(url));
        expect(await first.text()).toBe("old-theme");
        resolveNet(okResponse("new-theme"));
        await vi.waitFor(async () => {
            const cached = await (await caches.open(cacheName)).match(url);
            expect(await cached.text()).toBe("new-theme");
        });
    });

    it("leak oracle: findForbiddenCachedUrls catches api and ws entries", () => {
        expect(
            findForbiddenCachedUrls([
                `${ORIGIN}/assets/a.js`,
                `${ORIGIN}/api/v1/status`,
                `${ORIGIN}/ws`,
                "/boot-theme.js",
            ])
        ).toEqual(["/api/v1/status", "/ws"]);
    });
});

describe("swClientRegister update lifecycle oracle", () => {
    it("oracle: first install does not reload, update reloads once", () => {
        expect(decideControllerChangeReload({ hadController: false, refreshing: false })).toEqual({
            shouldReload: false,
            nextRefreshing: false,
        });
        const first = decideControllerChangeReload({ hadController: true, refreshing: false });
        expect(first).toEqual({ shouldReload: true, nextRefreshing: true });
        expect(decideControllerChangeReload({ hadController: true, refreshing: true })).toEqual({
            shouldReload: false,
            nextRefreshing: true,
        });
    });

    it("oracle: certificate errors are ignorable, others are not", () => {
        expect(isIgnorableServiceWorkerRegistrationError({ name: "SecurityError", message: "x" })).toBe(true);
        expect(
            isIgnorableServiceWorkerRegistrationError({ name: "TypeError", message: "SSL certificate problem" })
        ).toBe(true);
        expect(isIgnorableServiceWorkerRegistrationError({ name: "TypeError", message: "network down" })).toBe(false);
    });

    it("oracle: register options force updateViaCache none", () => {
        expect(serviceWorkerRegisterOptions()).toEqual({ updateViaCache: "none" });
    });
});
