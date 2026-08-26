// SPDX-License-Identifier: 0BSD

const UUID_V4_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

/**
 * @typedef {object} UuidCrypto
 * @property {(array: Uint8Array) => Uint8Array} [getRandomValues]
 * @property {() => string} [randomUUID]
 */

/**
 * @returns {UuidCrypto | undefined}
 */
function getCrypto() {
    if (typeof globalThis !== "undefined" && globalThis.crypto) {
        return /** @type {UuidCrypto} */ (globalThis.crypto);
    }
    return undefined;
}

/**
 * Resolve crypto source. Pass `crypto: null` to force the non-crypto fallback.
 *
 * @param {{ crypto?: UuidCrypto | null }} [options]
 * @returns {UuidCrypto | null | undefined}
 */
export function resolveCrypto(options = {}) {
    if (Object.prototype.hasOwnProperty.call(options, "crypto")) {
        return options.crypto;
    }
    return getCrypto();
}

/**
 * Fill a Uint8Array with cryptographically strong random values when possible.
 * Falls back to Math.random only when Web Crypto is unavailable.
 * Do not use the Math.random path for secrets.
 *
 * @param {Uint8Array} bytes
 * @param {{ crypto?: UuidCrypto | null }} [options]
 * @returns {Uint8Array}
 */
export function fillRandomBytes(bytes, options = {}) {
    if (!(bytes instanceof Uint8Array)) {
        throw new TypeError("fillRandomBytes expects a Uint8Array");
    }
    const c = resolveCrypto(options);
    if (c && typeof c.getRandomValues === "function") {
        c.getRandomValues(bytes);
        return bytes;
    }
    for (let i = 0; i < bytes.length; i++) {
        bytes[i] = Math.floor(Math.random() * 256) & 0xff;
    }
    return bytes;
}

/**
 * RFC 4122 version 4 UUID string.
 *
 * @param {{ crypto?: UuidCrypto | null }} [options]
 * @returns {string}
 */
export function randomUuidV4(options = {}) {
    const c = resolveCrypto(options);
    if (c && typeof c.randomUUID === "function") {
        return c.randomUUID();
    }
    const bytes = fillRandomBytes(new Uint8Array(16), { crypto: c ?? null });
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

/**
 * Alias matching the previous `uuid` package import style.
 *
 * @param {{ crypto?: UuidCrypto | null }} [options]
 * @returns {string}
 */
export function uuidv4(options) {
    return randomUuidV4(options);
}

/**
 * @param {unknown} value
 * @returns {boolean}
 */
export function isUuidV4(value) {
    return typeof value === "string" && UUID_V4_RE.test(value);
}

export { UUID_V4_RE };
