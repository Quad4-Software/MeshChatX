// SPDX-License-Identifier: 0BSD

import { MAX_CALL_SUGGESTIONS, MIN_HASH_HEX_LENGTH, TRUNCATED_HASH_LENGTH } from "./constants.js";
import type { ActiveCall, CallHistoryEntry, CallSuggestion, TelephoneContact } from "./types.js";

/**
 * Resolves contact matching a destination or identity hash
 */
export function resolveContactByHash(
    hash: string | null | undefined,
    contacts: TelephoneContact[]
): TelephoneContact | null {
    if (!hash || !Array.isArray(contacts)) return null;
    const search = hash.toLowerCase().trim();
    return (
        contacts.find(
            (c) =>
                (c.remote_identity_hash && c.remote_identity_hash.toLowerCase() === search) ||
                (c.lxmf_address && c.lxmf_address.toLowerCase() === search) ||
                (c.lxst_address && c.lxst_address.toLowerCase() === search) ||
                (c.remote_telephony_hash && c.remote_telephony_hash.toLowerCase() === search) ||
                (c.remote_destination_hash && c.remote_destination_hash.toLowerCase() === search)
        ) || null
    );
}

/**
 * Cleans and sanitizes a raw telephone address input string into a valid hash to call
 */
export function sanitizeCallInputHash(raw: string | null | undefined, contacts: TelephoneContact[] = []): string {
    if (!raw) return "";
    let cleaned = String(raw).trim();
    const hexMatch = cleaned.match(/[0-9a-fA-F]{32,64}/);
    if (hexMatch && hexMatch[0]) {
        cleaned = hexMatch[0].slice(0, MIN_HASH_HEX_LENGTH);
    }
    cleaned = cleaned.toLowerCase();

    const contactByName = contacts.find((c) => c.name && c.name.toLowerCase() === cleaned);
    if (contactByName) {
        return (
            contactByName.remote_identity_hash ||
            contactByName.remote_telephony_hash ||
            contactByName.lxst_address ||
            contactByName.lxmf_address ||
            cleaned
        );
    }

    return cleaned;
}

/**
 * Builds autocomplete call suggestions from contacts and recent call history
 */
export function buildCallSuggestions(params: {
    search: string;
    contacts: TelephoneContact[];
    callHistory: CallHistoryEntry[];
    isFocused?: boolean;
    limit?: number;
}): CallSuggestion[] {
    const { search, contacts, callHistory, isFocused = true, limit = MAX_CALL_SUGGESTIONS } = params;
    if (!isFocused) {
        return [];
    }

    const query = (search || "").toLowerCase().trim();
    const suggestions: CallSuggestion[] = [];
    const seenHashes = new Set<string>();

    if (Array.isArray(contacts)) {
        contacts.forEach((c) => {
            if (!c || !c.remote_identity_hash) return;
            const hashKey = c.remote_identity_hash.toLowerCase();
            if (!seenHashes.has(hashKey)) {
                const nameMatches = c.name ? c.name.toLowerCase().includes(query) : false;
                const hashMatches = hashKey.includes(query);
                if (!query || nameMatches || hashMatches) {
                    suggestions.push({
                        name: c.name || hashKey.slice(0, TRUNCATED_HASH_LENGTH),
                        hash: c.remote_telephony_hash || c.remote_destination_hash || c.remote_identity_hash,
                        type: "contact",
                        icon: "account",
                    });
                    seenHashes.add(hashKey);
                }
            }
        });
    }

    if (Array.isArray(callHistory)) {
        callHistory.forEach((h) => {
            if (!h || !h.remote_identity_hash) return;
            const hashKey = h.remote_identity_hash.toLowerCase();
            if (!seenHashes.has(hashKey)) {
                const nameMatches = h.remote_identity_name
                    ? h.remote_identity_name.toLowerCase().includes(query)
                    : false;
                const hashMatches = hashKey.includes(query);
                if (!query || nameMatches || hashMatches) {
                    suggestions.push({
                        name: h.remote_identity_name || hashKey.slice(0, TRUNCATED_HASH_LENGTH),
                        hash: h.remote_telephony_hash || h.remote_destination_hash || h.remote_identity_hash,
                        type: "history",
                        icon: "history",
                    });
                    seenHashes.add(hashKey);
                }
            }
        });
    }

    return suggestions.slice(0, limit);
}

/**
 * Hydrates contact images and visual assets onto active call and history entries
 */
export function hydrateContactVisuals(params: {
    contacts: TelephoneContact[];
    activeCall?: ActiveCall | null;
    lastCall?: ActiveCall | null;
    callHistory?: CallHistoryEntry[];
}): {
    activeCall?: ActiveCall | null;
    lastCall?: ActiveCall | null;
    callHistory: CallHistoryEntry[];
} {
    const { contacts, activeCall, lastCall, callHistory = [] } = params;
    const imageMap: Record<string, string> = {};

    if (Array.isArray(contacts)) {
        contacts.forEach((c) => {
            if (!c || !c.custom_image) return;
            const keys = [
                c.remote_identity_hash,
                c.lxmf_address,
                c.lxst_address,
                c.remote_destination_hash,
                c.remote_telephony_hash,
            ].filter((k): k is string => typeof k === "string" && k.length > 0);

            keys.forEach((k) => {
                imageMap[k.toLowerCase()] = c.custom_image as string;
            });
        });
    }

    const applyImage = (target: ActiveCall | null | undefined): void => {
        if (!target) return;
        const key =
            target.remote_identity_hash || target.remote_destination_hash || target.remote_telephony_hash;
        if (key && imageMap[key.toLowerCase()]) {
            target.custom_image = imageMap[key.toLowerCase()];
        }
    };

    applyImage(activeCall);
    applyImage(lastCall);

    const updatedHistory = callHistory.map((entry) => {
        const key =
            entry.remote_identity_hash || entry.remote_destination_hash || entry.remote_telephony_hash;
        if (key && imageMap[key.toLowerCase()]) {
            return { ...entry, contact_image: imageMap[key.toLowerCase()] };
        }
        return entry;
    });

    return {
        activeCall,
        lastCall,
        callHistory: updatedHistory,
    };
}

/**
 * Filters call history by search term
 */
export function filterCallHistory(history: CallHistoryEntry[], search: string): CallHistoryEntry[] {
    if (!Array.isArray(history)) return [];
    const query = (search || "").toLowerCase().trim();
    if (!query) return history;
    return history.filter((entry) => {
        const nameMatch = entry.remote_identity_name
            ? entry.remote_identity_name.toLowerCase().includes(query)
            : false;
        const hashMatch = entry.remote_identity_hash
            ? entry.remote_identity_hash.toLowerCase().includes(query)
            : false;
        return nameMatch || hashMatch;
    });
}
