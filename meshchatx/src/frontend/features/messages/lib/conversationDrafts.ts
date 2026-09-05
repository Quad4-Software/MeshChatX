// SPDX-License-Identifier: 0BSD

import { COMPOSE_DRAFT_STORAGE_PREFIX } from "./constants.js";

export function draftStorageKey(identityKey: string, destinationHash: string): string {
    return `${COMPOSE_DRAFT_STORAGE_PREFIX}${identityKey || "_"}:${(destinationHash || "").toLowerCase()}`;
}

export function loadDraft(destinationHash: string, identityKey: string): string {
    if (!destinationHash) {
        return "";
    }
    try {
        return localStorage.getItem(draftStorageKey(identityKey, destinationHash)) || "";
    } catch {
        return "";
    }
}

export function saveDraft(destinationHash: string, identityKey: string, text: string): void {
    if (!destinationHash) {
        return;
    }
    const key = draftStorageKey(identityKey, destinationHash);
    try {
        if (!text) {
            localStorage.removeItem(key);
        } else {
            localStorage.setItem(key, text);
        }
    } catch {
        /* ignore */
    }
}
