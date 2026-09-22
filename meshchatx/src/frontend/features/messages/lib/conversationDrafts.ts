// SPDX-License-Identifier: 0BSD

import { COMPOSE_DRAFT_STORAGE_PREFIX, LEGACY_COMPOSE_DRAFTS_STORAGE_KEY } from "./constants.js";

export function draftStorageKey(identityKey: string, destinationHash: string): string {
    return `${COMPOSE_DRAFT_STORAGE_PREFIX}${identityKey || "_"}:${(destinationHash || "").toLowerCase()}`;
}

function readLegacyDraftRoot(): Record<string, unknown> {
    try {
        const raw = JSON.parse(localStorage.getItem(LEGACY_COMPOSE_DRAFTS_STORAGE_KEY) || "{}");
        return raw && typeof raw === "object" && !Array.isArray(raw) ? (raw as Record<string, unknown>) : {};
    } catch {
        return {};
    }
}

function legacyBucketFor(drafts: Record<string, unknown>, identityKey: string): Record<string, unknown> | null {
    const nested = drafts[identityKey || "_"];
    if (nested && typeof nested === "object" && !Array.isArray(nested)) {
        return nested as Record<string, unknown>;
    }
    return null;
}

function hasNestedLegacyBuckets(drafts: Record<string, unknown>): boolean {
    return Object.values(drafts).some((value) => value && typeof value === "object" && !Array.isArray(value));
}

function lookupLegacyDraftText(destinationHash: string, identityKey: string): string {
    if (!destinationHash) {
        return "";
    }
    const drafts = readLegacyDraftRoot();
    const key = identityKey || "_";
    const destKeys = [destinationHash, destinationHash.toLowerCase()];
    const bucket = legacyBucketFor(drafts, key);
    if (bucket) {
        for (const dest of destKeys) {
            const text = bucket[dest];
            if (typeof text === "string") {
                return text;
            }
        }
    }
    if (!hasNestedLegacyBuckets(drafts)) {
        for (const dest of destKeys) {
            const text = drafts[dest];
            if (typeof text === "string") {
                return text;
            }
        }
    }
    return "";
}

export function loadDraft(destinationHash: string, identityKey: string): string {
    if (!destinationHash) {
        return "";
    }
    try {
        const modern = localStorage.getItem(draftStorageKey(identityKey, destinationHash));
        if (modern) {
            return modern;
        }
        const legacy = lookupLegacyDraftText(destinationHash, identityKey);
        if (legacy) {
            saveDraft(destinationHash, identityKey, legacy);
            return legacy;
        }
        return "";
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
