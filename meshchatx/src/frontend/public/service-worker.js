// SPDX-License-Identifier: 0BSD

/* eslint-disable no-restricted-globals */

/* Generated MeshChatX service worker. Do not edit by hand. */

/** Prefix for versioned Cache Storage buckets. */
const SHELL_CACHE_PREFIX = "meshchatx-shell-";

/** Default navigation network-first timeout in milliseconds. */
const NAV_NETWORK_TIMEOUT_MS = 2000;

export type ShellRequestKind = "bypass" | "asset" | "navigation" | "shell-helper" | "network-only";

function cacheNameForBuild(buildId: string): string {
    const id = String(buildId || "dev").replace(/[^a-zA-Z0-9._-]/g, "_");
    return `${SHELL_CACHE_PREFIX}v${id}`;
}

function isApiPath(pathname: string): boolean {
    const path = String(pathname || "");
    return path === "/api" || path.startsWith("/api/");
}

/** Vite content-hashed build assets under /assets/. */
function isHashedAssetPath(pathname: string): boolean {
    const path = String(pathname || "");
    return path === "/assets" || path.startsWith("/assets/");
}

/** Static shell helpers that may use stale-while-revalidate. */
function isShellHelperPath(pathname: string): boolean {
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

function isNavigationRequest(request: Request): boolean {
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

/** True when the service worker must not use Cache Storage for this request. */
function shouldBypassCache(request: Request, url?: URL): boolean {
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

/** Classify a same-origin GET for shell caching strategy selection. */
function classifyShellRequest(request: Request, url: URL): ShellRequestKind {
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

export type OracleStrategyInput = {
    method?: string;
    pathname?: string;
    mode?: string;
    destination?: string;
    accept?: string;
};

/**
 * Independent accept/reject oracle for shell caching.
 * Predicts strategy from raw inputs without calling classifyShellRequest.
 */
function oracleExpectedStrategy(input: OracleStrategyInput): ShellRequestKind {
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

function selectCachesToDelete(cacheKeys: string[], prefix: string, currentName: string): string[] {
    const keys = Array.isArray(cacheKeys) ? cacheKeys : [];
    return keys.filter((key) => typeof key === "string" && key.startsWith(prefix) && key !== currentName);
}

function findForbiddenCachedUrls(urls: Iterable<string>): string[] {
    const leaked: string[] = [];
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

export type ShellRuntimeOptions = {
    caches: CacheStorage;
    fetch: typeof fetch;
    cacheName: string;
    origin: string;
    shellFallbackUrl?: string;
    navTimeoutMs?: number;
    setTimeout?: typeof setTimeout;
    clearTimeout?: typeof clearTimeout;
};

export type FetchEventExtras = {
    preloadResponse?: Promise<Response | null>;
};

export type ShellRuntime = {
    cacheFirst: (request: Request) => Promise<Response>;
    staleWhileRevalidate: (request: Request) => Promise<Response>;
    networkFirstNavigation: (eventLike: {
        request: Request;
        preloadResponse?: Promise<Response | null>;
    }) => Promise<Response>;
    pruneOldShellCaches: () => Promise<string[]>;
    putInCache: (request: Request, response: Response) => Promise<void>;
    cacheShellSnapshot: (response: Response) => Promise<void>;
    resolveFetch: (request: Request, extras?: FetchEventExtras) => Promise<Response> | null;
    cacheName: string;
    shellFallbackUrl: string;
};

/** Create injectable shell cache strategies for the service worker (and tests). */
function createShellRuntime(options: ShellRuntimeOptions): ShellRuntime {
    const cachesApi = options.caches;
    const fetchFn = options.fetch;
    const cacheName = options.cacheName;
    const origin = options.origin;
    const shellFallbackUrl = options.shellFallbackUrl || SHELL_FALLBACK_URL;
    const navTimeoutMs = options.navTimeoutMs ?? NAV_NETWORK_TIMEOUT_MS;
    const setTimeoutFn = options.setTimeout || setTimeout;
    const clearTimeoutFn = options.clearTimeout || clearTimeout;

    async function putInCache(request: Request, response: Response): Promise<void> {
        if (!response || !response.ok) {
            return;
        }
        const cache = await cachesApi.open(cacheName);
        await cache.put(request, response);
    }

    async function cacheShellSnapshot(response: Response): Promise<void> {
        if (!response || !response.ok) {
            return;
        }
        const cache = await cachesApi.open(cacheName);
        await cache.put(shellFallbackUrl, response.clone());
    }

    async function networkWithTimeout(request: Request, timeoutMs: number): Promise<Response> {
        const controller = new AbortController();
        const timer = setTimeoutFn(() => controller.abort(), timeoutMs);
        try {
            return await fetchFn(request, { signal: controller.signal });
        } finally {
            clearTimeoutFn(timer);
        }
    }

    async function cacheFirst(request: Request): Promise<Response> {
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

    async function staleWhileRevalidate(request: Request): Promise<Response> {
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

    async function networkFirstNavigation(eventLike: {
        request: Request;
        preloadResponse?: Promise<Response | null>;
    }): Promise<Response> {
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

    async function pruneOldShellCaches(): Promise<string[]> {
        const keys = await cachesApi.keys();
        const doomed = selectCachesToDelete(keys, SHELL_CACHE_PREFIX, cacheName);
        await Promise.all(doomed.map((key) => cachesApi.delete(key)));
        return doomed;
    }

    /** null means network bypass (do not respondWith) */
    function resolveFetch(request: Request, eventExtras: FetchEventExtras = {}): Promise<Response> | null {
        let url: URL;
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

/** Await navigation preload without throwing when Chrome cancels it. */
async function settlePreloadResponse(
    preloadResponse: Promise<Response | null> | null | undefined
): Promise<Response | null> {
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
 */
function shouldAttachNavigationPreload(request: Request, origin: string): boolean {
    if (!request || typeof request.url !== "string") {
        return false;
    }
    let url: URL;
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

export type FetchEventLike = {
    request: Request;
    preloadResponse?: Promise<Response | null>;
    respondWith: (p: Promise<Response>) => void;
};

/**
 * Fetch listener: touch preloadResponse only when this event will respondWith a navigation.
 * Returns true when respondWith was called.
 */
function handleFetchEvent(
    event: FetchEventLike,
    runtime: Pick<ShellRuntime, "resolveFetch">,
    origin: string
): boolean {
    const extras: FetchEventExtras = {};
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

// SPDX-License-Identifier: 0BSD
/* global ["/","/boot-theme.js","/manifest.json","/favicons/favicon-512x512.png"], cacheNameForBuild, createShellRuntime, handleFetchEvent, SHELL_FALLBACK_URL, NAV_NETWORK_TIMEOUT_MS, UPDATE_MESSAGE_TYPE */
/**
 * MeshChatX app-shell service worker bootstrap.
 * Preceded at build time by inlined swCachePolicy.ts + swShellRuntime.ts.
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
    handleFetchEvent(event, runtime, self.location.origin);
});
