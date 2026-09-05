// SPDX-License-Identifier: 0BSD

/**
 * Resolve integrity.json key for an RNode flasher script URL.
 * Tries longest suffix first so both flat files (zip.min.js) and nested
 * packages (crypto-js@x/core.js, web-serial-polyfill@x/dist/serial.js) match.
 *
 * @param {string} src
 * @param {Record<string, string>|null|undefined} integrity
 * @returns {string}
 */
export function rnodeIntegrityKeyForSrc(src, integrity) {
    const parts = String(src || "")
        .split("/")
        .filter(Boolean);
    if (parts.length === 0) {
        return "";
    }
    const candidates: string[] = [];
    for (let n = Math.min(3, parts.length); n >= 1; n -= 1) {
        candidates.push(parts.slice(-n).join("/"));
    }
    if (integrity && typeof integrity === "object") {
        for (const key of candidates) {
            if (integrity[key]) {
                return key;
            }
        }
    }
    return candidates[candidates.length - 1] || parts[parts.length - 1];
}
