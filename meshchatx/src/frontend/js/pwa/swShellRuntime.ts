// SPDX-License-Identifier: 0BSD

import { NAV_NETWORK_TIMEOUT_MS, SHELL_CACHE_PREFIX, classifyShellRequest } from "./swCachePolicy.js";

export const SHELL_FALLBACK_URL = "/";
export const UPDATE_MESSAGE_TYPE = "meshchatx-sw-updated";

/**
 * Independent accept/reject oracle for shell caching.
 * Predicts strategy from raw inputs without calling classifyShellRequest.
 * @param {{ method?: string, pathname?: string, mode?: string, destination?: string, accept?: string }} input
 * @returns {"bypass"|"asset"|"navigation"|"shell-helper"|"network-only"}
 */
export function oracleExpectedStrategy(input) {
    const method = input.method || "GET";
    const pathname = String(input.pathname || "/");
    if (method !== "GET" && method !== "HEAD") {
        return "bypass";
    }
    if (pathname === "/api" || pathname.startsWith("/api/")) {
        return "bypass";
    }
    if (pathname === "/ws" || pathname.startsWith("/ws/")) {
        return "bypass";
    }
    if (pathname === "/service-worker.js") {
        return "bypass";
    }
    if (pathname === "/assets" || pathname.startsWith("/assets/")) {
        return "asset";
    }
    const navigate =
        input.mode === "navigate" ||
        input.destination === "document" ||
        (typeof input.accept === "string" && input.accept.includes("text/html")) ||
        pathname === "/" ||
        pathname === "/index.html";
    if (navigate) {
        return "navigation";
    }
    if (
        pathname === "/boot-theme.js" ||
        pathname === "/manifest.json" ||
        pathname === "/favicons" ||
        pathname.startsWith("/favicons/") ||
        /favicon/i.test(pathname)
    ) {
        return "shell-helper";
    }
    return "network-only";
}

/**
 * @param {string[]} cacheKeys
 * @param {string} prefix
 * @param {string} currentName
 * @returns {string[]}
 */
export function selectCachesToDelete(cacheKeys, prefix, currentName) {
    const keys = Array.isArray(cacheKeys) ? cacheKeys : [];
    return keys.filter((key) => typeof key === "string" && key.startsWith(prefix) && key !== currentName);
}

/**
 * @param {Iterable<string>} urls
 * @returns {string[]}
 */
export function findForbiddenCachedUrls(urls) {
    const leaked = [];
    for (const raw of urls || []) {
        let pathname = String(raw || "");
        try {
            if (pathname.includes("://")) {
                pathname = new URL(pathname).pathname;
            }
        } catch {
            // keep raw
        }
        if (pathname === "/api" || pathname.startsWith("/api/") || pathname === "/ws" || pathname.startsWith("/ws/")) {
            leaked.push(pathname);
        }
    }
    return leaked;
}

/**
 * Create injectable shell cache strategies for the service worker (and tests).
 * @param {{
 *   caches: CacheStorage,
 *   fetch: typeof fetch,
 *   cacheName: string,
 *   origin: string,
 *   shellFallbackUrl?: string,
 *   navTimeoutMs?: number,
 *   setTimeout?: typeof setTimeout,
 *   clearTimeout?: typeof clearTimeout,
 * }} options
 */
export function createShellRuntime(options) {
    const cachesApi = options.caches;
    const fetchFn = options.fetch;
    const cacheName = options.cacheName;
    const origin = options.origin;
    const shellFallbackUrl = options.shellFallbackUrl || SHELL_FALLBACK_URL;
    const navTimeoutMs = options.navTimeoutMs ?? NAV_NETWORK_TIMEOUT_MS;
    const setTimeoutFn = options.setTimeout || setTimeout;
    const clearTimeoutFn = options.clearTimeout || clearTimeout;

    async function putInCache(request, response) {
        if (!response || !response.ok) {
            return;
        }
        const cache = await cachesApi.open(cacheName);
        await cache.put(request, response);
    }

    async function cacheShellSnapshot(response) {
        if (!response || !response.ok) {
            return;
        }
        const cache = await cachesApi.open(cacheName);
        await cache.put(shellFallbackUrl, response.clone());
    }

    async function networkWithTimeout(request, timeoutMs) {
        const controller = new AbortController();
        const timer = setTimeoutFn(() => controller.abort(), timeoutMs);
        try {
            return await fetchFn(request, { signal: controller.signal });
        } finally {
            clearTimeoutFn(timer);
        }
    }

    async function cacheFirst(request) {
        const cached = await cachesApi.match(request);
        if (cached) {
            return cached;
        }
        const response = await fetchFn(request);
        if (response && response.ok) {
            await putInCache(request, response.clone());
        }
        return response;
    }

    async function staleWhileRevalidate(request) {
        const cache = await cachesApi.open(cacheName);
        const cached = await cache.match(request);
        const networkPromise = fetchFn(request)
            .then((response) => {
                if (response && response.ok) {
                    void cache.put(request, response.clone());
                }
                return response;
            })
            .catch(() => null);
        if (cached) {
            void networkPromise;
            return cached;
        }
        const networkResponse = await networkPromise;
        if (networkResponse) {
            return networkResponse;
        }
        throw new Error("shell helper unavailable");
    }

    async function networkFirstNavigation(eventLike) {
        const request = eventLike.request;
        try {
            let response = await settlePreloadResponse(eventLike.preloadResponse);
            if (!response) {
                response = await networkWithTimeout(request, navTimeoutMs);
            }
            if (response && response.ok) {
                await cacheShellSnapshot(response.clone());
                return response;
            }
        } catch {
            // fall through to cache
        }
        const cached = (await cachesApi.match(shellFallbackUrl)) || (await cachesApi.match(request));
        if (cached) {
            return cached;
        }
        return fetchFn(request);
    }

    async function pruneOldShellCaches() {
        const keys = await cachesApi.keys();
        const doomed = selectCachesToDelete(keys, SHELL_CACHE_PREFIX, cacheName);
        await Promise.all(doomed.map((key) => cachesApi.delete(key)));
        return doomed;
    }

    /**
     * @param {Request} request
     * @param {{ preloadResponse?: Promise<Response|null> }} [eventExtras]
     * @returns {Promise<Response>|null} null means network bypass (do not respondWith)
     */
    function resolveFetch(request, eventExtras: any = {}) {
        let url;
        try {
            url = new URL(request.url);
        } catch {
            return null;
        }
        if (url.origin !== origin) {
            return null;
        }
        const kind = classifyShellRequest(request, url);
        if (kind === "bypass" || kind === "network-only") {
            return null;
        }
        if (kind === "asset") {
            return cacheFirst(request);
        }
        if (kind === "shell-helper") {
            return staleWhileRevalidate(request);
        }
        if (kind === "navigation") {
            return networkFirstNavigation({ request, preloadResponse: eventExtras.preloadResponse });
        }
        return null;
    }

    return {
        cacheFirst,
        staleWhileRevalidate,
        networkFirstNavigation,
        pruneOldShellCaches,
        putInCache,
        cacheShellSnapshot,
        resolveFetch,
        cacheName,
        shellFallbackUrl,
    };
}

/**
 * Await navigation preload without throwing when Chrome cancels it.
 * @param {Promise<Response|null>|null|undefined} preloadResponse
 * @returns {Promise<Response|null>}
 */
export async function settlePreloadResponse(preloadResponse) {
    if (preloadResponse == null) {
        return null;
    }
    try {
        return await preloadResponse;
    } catch {
        return null;
    }
}

/**
 * True only for same-origin navigations that resolveFetch will handle.
 * Accessing event.preloadResponse without respondWith throws NetworkError on cancel.
 * @param {Request} request
 * @param {string} origin
 * @returns {boolean}
 */
export function shouldAttachNavigationPreload(request, origin) {
    if (!request || typeof request.url !== "string") {
        return false;
    }
    let url;
    try {
        url = new URL(request.url);
    } catch {
        return false;
    }
    if (url.origin !== origin) {
        return false;
    }
    return classifyShellRequest(request, url) === "navigation";
}

/**
 * Fetch listener: touch preloadResponse only when this event will respondWith a navigation.
 * @param {{ request: Request, preloadResponse?: Promise<Response|null>, respondWith: (p: Promise<Response>) => void }} event
 * @param {{ resolveFetch: (request: Request, extras?: object) => Promise<Response>|null }} runtime
 * @param {string} origin
 * @returns {boolean} true when respondWith was called
 */
export function handleFetchEvent(event, runtime, origin) {
    const extras: any = {};
    if (shouldAttachNavigationPreload(event.request, origin)) {
        extras.preloadResponse = event.preloadResponse;
    }
    const handled = runtime.resolveFetch(event.request, extras);
    if (handled) {
        event.respondWith(handled);
        return true;
    }
    return false;
}
