// SPDX-License-Identifier: 0BSD

/**
 * @param {unknown} value
 * @returns {boolean}
 */
export function isValidForwarderDestinationHash(value) {
    const hash = String(value || "").trim();
    return hash.length === 32 && /^[0-9a-fA-F]+$/.test(hash);
}
