// SPDX-License-Identifier: 0BSD

/**
 * Hostname classification for map tile / nominatim "local" checks.
 */

/**
 * True when hostname is loopback, .local, or RFC1918 private.
 * @param {string} hostname
 * @returns {boolean}
 */
/**
 * True when host is a dotted-quad IPv4 in loopback or RFC1918 space.
 * Hostname prefixes such as 10.evil.com are not private.
 * @param {string} host
 * @returns {boolean}
 */
function isPrivateOrLoopbackIPv4(host) {
    const m = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/.exec(host);
    if (!m) {
        return false;
    }
    const a = Number(m[1]);
    const b = Number(m[2]);
    const c = Number(m[3]);
    const d = Number(m[4]);
    if (a > 255 || b > 255 || c > 255 || d > 255) {
        return false;
    }
    if (a === 127) {
        return true;
    }
    if (a === 10) {
        return true;
    }
    if (a === 192 && b === 168) {
        return true;
    }
    if (a === 172 && b >= 16 && b <= 31) {
        return true;
    }
    return false;
}

export function isPrivateOrLocalHostname(hostname) {
    const host = String(hostname || "")
        .trim()
        .toLowerCase()
        .replace(/^\[|\]$/g, "");
    if (!host) {
        return false;
    }
    if (host === "localhost" || host === "::1" || host === "0:0:0:0:0:0:0:1") {
        return true;
    }
    if (host.endsWith(".local")) {
        return true;
    }
    return isPrivateOrLoopbackIPv4(host);
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
