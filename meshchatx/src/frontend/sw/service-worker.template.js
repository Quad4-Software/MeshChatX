// SPDX-License-Identifier: 0BSD
/* global __MESHCHATX_SW_PRECACHE_JSON__, cacheNameForBuild, createShellRuntime, handleFetchEvent, SHELL_FALLBACK_URL, NAV_NETWORK_TIMEOUT_MS, UPDATE_MESSAGE_TYPE */
/**
 * MeshChatX app-shell service worker bootstrap.
 * Preceded at build time by inlined swCachePolicy.ts + swShellRuntime.ts.
 * Placeholders __MESHCHATX_SW_BUILD_ID__ and __MESHCHATX_SW_PRECACHE_JSON__ are replaced.
 */

const BUILD_ID = "__MESHCHATX_SW_BUILD_ID__";
const PRECACHE_URLS = __MESHCHATX_SW_PRECACHE_JSON__;
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
