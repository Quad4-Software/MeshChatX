// SPDX-License-Identifier: 0BSD

export function isValidForwarderDestinationHash(value: unknown): boolean {
    const hash = String(value || "").trim();
    return hash.length === 32 && /^[0-9a-fA-F]+$/.test(hash);
}
