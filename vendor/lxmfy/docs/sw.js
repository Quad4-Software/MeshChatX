/* LXMFy docs service worker.
   Keeps the docs readable offline and refreshes cached pages whenever
   the browser is online, so new deployments appear on the next load.

   Strategy:
   - HTML navigations: network first, cache fallback. Online readers
     always see the newest pages; offline readers get the cached copy.
   - Site assets (css/js/images): cache first, they are content hashed
     and effectively immutable between builds.
   - Everything else (fonts, cross origin): stale while revalidate.

   Paths are derived from this script's own URL so the worker works
   whether the site is mounted at the origin root or a subpath. */
"use strict";

const VERSION = "v1";
const PAGES = `lxmfy-pages-${VERSION}`;
const ASSETS = `lxmfy-assets-${VERSION}`;

const BASE = new URL("./", self.location.href);

const rel = (path) => new URL(path, BASE).pathname;

const CORE = [
  "",
  "quick-start/",
  "creating-bots/",
  "api-reference/",
  "manifest.webmanifest",
  "assets/icon-192.png",
  "assets/icon-512.png",
  "assets/favicon.svg",
  "assets/logo.svg",
].map(rel);

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(PAGES).then((cache) => cache.addAll(CORE)).then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== PAGES && key !== ASSETS)
          .map((key) => caches.delete(key)),
      ),
    ).then(() => self.clients.claim()),
  );
});

const isPageRequest = (request) =>
  request.mode === "navigate" ||
  (request.headers.get("accept") || "").includes("text/html");

const isAssetRequest = (url) =>
  url.origin === location.origin &&
  url.pathname.startsWith(BASE.pathname) &&
  (url.pathname.includes("/assets/") ||
    url.pathname.endsWith(".css") ||
    url.pathname.endsWith(".js") ||
    url.pathname.endsWith(".woff2") ||
    url.pathname.endsWith(".svg") ||
    url.pathname.endsWith(".png"));

const networkFirst = async (request) => {
  const cache = await caches.open(PAGES);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch {
    const cached = await cache.match(request, { ignoreSearch: true });
    return cached || cache.match(rel(""));
  }
};

const cacheFirst = async (request) => {
  const cache = await caches.open(ASSETS);
  const cached = await cache.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) cache.put(request, response.clone());
  return response;
};

const staleWhileRevalidate = async (request) => {
  const cache = await caches.open(ASSETS);
  const cached = await cache.match(request);
  const fetched = fetch(request)
    .then((response) => {
      if (response.ok || response.type === "opaque") {
        cache.put(request, response.clone());
      }
      return response;
    })
    .catch(() => undefined);
  return cached || fetched;
};

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (isPageRequest(request)) {
    event.respondWith(networkFirst(request));
  } else if (isAssetRequest(url)) {
    event.respondWith(cacheFirst(request));
  } else {
    event.respondWith(staleWhileRevalidate(request));
  }
});
