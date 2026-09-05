// SPDX-License-Identifier: 0BSD

function normalizeHash(value: unknown): string {
    return typeof value === "string" ? value.trim().toLowerCase() : "";
}

export function isSelfLxmfDestination(peerHash: unknown, myLxmfAddressHash: unknown, identityHash: unknown): boolean {
    const peer = normalizeHash(peerHash);
    if (!peer) {
        return false;
    }
    return peer === normalizeHash(myLxmfAddressHash) || peer === normalizeHash(identityHash);
}
