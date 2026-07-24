// SPDX-License-Identifier: 0BSD

/** Prefix for versioned Cache Storage buckets. */
export const SHELL_CACHE_PREFIX = "meshchatx-shell-";

/** Default navigation network-first timeout in milliseconds. */
export const NAV_NETWORK_TIMEOUT_MS = 2000;

/**
 * @param {string} buildId
 * @returns {string}
 */
export function cacheNameForBuild(buildId) {
    const id = String(buildId || "dev").replace(/[^a-zA-Z0-9._-]/g, "_");
    return `${SHELL_CACHE_PREFIX}v${id}`;
}

/**
 * @param {string} pathname
 * @returns {boolean}
 */
export function isApiPath(pathname) {
    const path = String(pathname || "");
    return path === "/api" || path.startsWith("/api/");
}

/**
 * Vite content-hashed build assets under /assets/.
 * @param {string} pathname
 * @returns {boolean}
 */
export function isHashedAssetPath(pathname) {
    const path = String(pathname || "");
    return path === "/assets" || path.startsWith("/assets/");
}

/**
 * Static shell helpers that may use stale-while-revalidate.
 * @param {string} pathname
 * @returns {boolean}
 */
export function isShellHelperPath(pathname) {
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
export function isNavigationRequest(request) {
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
export function shouldBypassCache(request, url) {
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
export function classifyShellRequest(request, url) {
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
