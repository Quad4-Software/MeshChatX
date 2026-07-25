// SPDX-License-Identifier: 0BSD

/* eslint-disable no-restricted-globals */

/* Generated MeshChatX service worker. Do not edit by hand. */

/** Prefix for versioned Cache Storage buckets. */
const SHELL_CACHE_PREFIX = "meshchatx-shell-";

/** Default navigation network-first timeout in milliseconds. */
const NAV_NETWORK_TIMEOUT_MS = 2000;

/**
 * @param {string} buildId
 * @returns {string}
 */
function cacheNameForBuild(buildId) {
    const id = String(buildId || "dev").replace(/[^a-zA-Z0-9._-]/g, "_");
    return `${SHELL_CACHE_PREFIX}v${id}`;
}

/**
 * @param {string} pathname
 * @returns {boolean}
 */
function isApiPath(pathname) {
    const path = String(pathname || "");
    return path === "/api" || path.startsWith("/api/");
}

/**
 * Vite content-hashed build assets under /assets/.
 * @param {string} pathname
 * @returns {boolean}
 */
function isHashedAssetPath(pathname) {
    const path = String(pathname || "");
    return path === "/assets" || path.startsWith("/assets/");
}

/**
 * Static shell helpers that may use stale-while-revalidate.
 * @param {string} pathname
 * @returns {boolean}
 */
function isShellHelperPath(pathname) {
    const path = String(pathname || "");
    if (path === "/boot-theme.js" || path === "/manifest.json") {
        return true;
    }
    if (path === "/favicons" || path.startsWith("/favicons/")) {
        return true;
    }
    if (/favicon/i.test(path)) {
        return true;
    }
    return false;
}

/**
 * @param {Request} request
 * @returns {boolean}
 */
function isNavigationRequest(request) {
    if (!request || typeof request !== "object") {
        return false;
    }
    if (request.mode === "navigate") {
        return true;
    }
    const dest = request.destination;
    if (dest === "document") {
        return true;
    }
    const accept = request.headers?.get?.("accept") || "";
    return typeof accept === "string" && accept.includes("text/html");
}

/**
 * True when the service worker must not use Cache Storage for this request.
 * @param {Request} request
 * @param {URL} [url]
 * @returns {boolean}
 */
function shouldBypassCache(request, url) {
    if (!request || (request.method !== "GET" && request.method !== "HEAD")) {
        return true;
    }
    let pathname = "/";
    if (url && typeof url.pathname === "string") {
        pathname = url.pathname;
    } else if (typeof request.url === "string") {
        try {
            pathname = new URL(request.url).pathname;
        } catch {
            return true;
        }
    }
    if (isApiPath(pathname)) {
        return true;
    }
    if (pathname === "/ws" || pathname.startsWith("/ws/")) {
        return true;
    }
    if (pathname === "/service-worker.js") {
        return true;
    }
    return false;
}

/**
 * Classify a same-origin GET for shell caching strategy selection.
 * @param {Request} request
 * @param {URL} url
 * @returns {"bypass"|"asset"|"navigation"|"shell-helper"|"network-only"}
 */
function classifyShellRequest(request, url) {
    if (shouldBypassCache(request, url)) {
        return "bypass";
    }
    const pathname = url.pathname;
    if (isHashedAssetPath(pathname)) {
        return "asset";
    }
    if (isNavigationRequest(request) || pathname === "/" || pathname === "/index.html") {
        return "navigation";
    }
    if (isShellHelperPath(pathname)) {
        return "shell-helper";
    }
    return "network-only";
}

const SHELL_FALLBACK_URL = "/";
const UPDATE_MESSAGE_TYPE = "meshchatx-sw-updated";

/**
 * Independent accept/reject oracle for shell caching.
 * Predicts strategy from raw inputs without calling classifyShellRequest.
 * @param {{ method?: string, pathname?: string, mode?: string, destination?: string, accept?: string }} input
 * @returns {"bypass"|"asset"|"navigation"|"shell-helper"|"network-only"}
 */
function oracleExpectedStrategy(input) {
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
function selectCachesToDelete(cacheKeys, prefix, currentName) {
    const keys = Array.isArray(cacheKeys) ? cacheKeys : [];
    return keys.filter((key) => typeof key === "string" && key.startsWith(prefix) && key !== currentName);
}

/**
 * @param {Iterable<string>} urls
 * @returns {string[]}
 */
function findForbiddenCachedUrls(urls) {
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
function createShellRuntime(options) {
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
            let response = null;
            if (eventLike.preloadResponse) {
                response = await eventLike.preloadResponse;
            }
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
    function resolveFetch(request, eventExtras = {}) {
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

// SPDX-License-Identifier: 0BSD
/* global ["/","/boot-theme.js","/manifest.json","/favicons/favicon-512x512.png"], cacheNameForBuild, createShellRuntime, SHELL_FALLBACK_URL, NAV_NETWORK_TIMEOUT_MS, UPDATE_MESSAGE_TYPE */
/**
 * MeshChatX app-shell service worker bootstrap.
 * Preceded at build time by inlined swCachePolicy.js + swShellRuntime.js.
 * Placeholders dev and ["/","/boot-theme.js","/manifest.json","/favicons/favicon-512x512.png"] are replaced.
 */

const BUILD_ID = "dev";
const PRECACHE_URLS = ["/","/boot-theme.js","/manifest.json","/favicons/favicon-512x512.png"];
const CACHE_NAME = cacheNameForBuild(BUILD_ID);

const runtime = createShellRuntime({
    caches: self.caches,
    fetch: (...args) => self.fetch(...args),
    cacheName: CACHE_NAME,
    origin: self.location.origin,
    shellFallbackUrl: SHELL_FALLBACK_URL,
    navTimeoutMs: NAV_NETWORK_TIMEOUT_MS,
});

self.addEventListener("install", (event) => {
    event.waitUntil(
        (async () => {
            const cache = await self.caches.open(CACHE_NAME);
            const urls = Array.isArray(PRECACHE_URLS) ? PRECACHE_URLS : [];
            for (const url of urls) {
                try {
                    await cache.add(url);
                } catch {
                    // Skip missing optional assets during install
                }
            }
            await self.skipWaiting();
        })()
    );
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        (async () => {
            if (self.registration && self.registration.navigationPreload) {
                try {
                    await self.registration.navigationPreload.enable();
                } catch {
                    // navigation preload unsupported or denied
                }
            }
            await runtime.pruneOldShellCaches();
            await self.clients.claim();
            const clients = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
            for (const client of clients) {
                client.postMessage({ type: UPDATE_MESSAGE_TYPE, buildId: BUILD_ID });
            }
        })()
    );
});

self.addEventListener("message", (event) => {
    const data = event.data;
    if (!data || typeof data !== "object") {
        return;
    }
    if (data.type === "meshchatx-sw-skip-waiting") {
        void self.skipWaiting();
    }
});

self.addEventListener("fetch", (event) => {
    const handled = runtime.resolveFetch(event.request, {
        preloadResponse: event.preloadResponse,
    });
    if (handled) {
        event.respondWith(handled);
    }
});
