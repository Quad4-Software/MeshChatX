// SPDX-License-Identifier: 0BSD

/**
 * Hostname classification for map tile / nominatim "local" checks.
 */

/**
 * True when hostname is loopback, .local, or RFC1918 private.
 * @param {string} hostname
 * @returns {boolean}
 */
export function isPrivateOrLocalHostname(hostname) {
    const host = String(hostname || "")
        .trim()
        .toLowerCase()
        .replace(/^\[|\]$/g, "");
    if (!host) {
        return false;
    }
    if (host === "localhost" || host === "127.0.0.1" || host === "::1" || host === "0:0:0:0:0:0:0:1") {
        return true;
    }
    if (host.endsWith(".local")) {
        return true;
    }
    if (host.startsWith("10.")) {
        return true;
    }
    if (host.startsWith("192.168.")) {
        return true;
    }
    const m = /^172\.(\d+)\./.exec(host);
    if (m) {
        const second = Number(m[1]);
        return second >= 16 && second <= 31;
    }
    return false;
}

/**
 * True when a tile/nominatim URL should be treated as local / offline-reachable.
 * @param {string} url
 * @param {string} [origin]
 * @returns {boolean}
 */
export function isLocalMapServiceUrl(url, origin = typeof window !== "undefined" ? window.location.origin : "") {
    if (!url) {
        return false;
    }
    const raw = String(url);
    if (raw.startsWith("/") || raw.startsWith("./")) {
        return true;
    }
    try {
        const urlObj = new URL(raw, origin || "http://127.0.0.1");
        return isPrivateOrLocalHostname(urlObj.hostname);
    } catch {
        return !raw.startsWith("http");
    }
}
