// SPDX-License-Identifier: 0BSD

/**
 * Shared destination-hash checks for mesh UI input (LXMF, RRC hubs, tools).
 */

import Utils from "./Utils.js";

/** Case-insensitive 32 hex digits (Reticulum truncated destination hash). */
export const DESTINATION_HASH_RE = /^[0-9a-f]{32}$/i;

/**
 * True when value is exactly 32 hex digits after trim (no URI junk stripping).
 */
export function isDestinationHash(value: unknown): boolean {
    if (value == null) {
        return false;
    }
    const hash = String(value).trim();
    return hash.length === 32 && DESTINATION_HASH_RE.test(hash);
}

/**
 * Strip URI/punctuation via Utils.normalizeMeshchatHashHex, then require a valid hash.
 * Returns lowercase hex or empty string.
 */
export function normalizeDestinationHash(value: unknown): string {
    const hex = Utils.normalizeMeshchatHashHex(value);
    if (!isDestinationHash(hex)) {
        return "";
    }
    return hex.toLowerCase();
}
