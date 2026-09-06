// SPDX-License-Identifier: 0BSD

import {
    DEFAULT_BLOCKLIST_MATCH_MESSAGE,
    DEFAULT_BLOCKLIST_MATCH_MODE,
    DEFAULT_BLOCKLIST_MATCH_PEER_FIELDS,
    DEFAULT_BLOCKLIST_SCOPE,
    ID_RANDOM_RADIX,
    ID_SLICE_END,
    ID_SLICE_START,
} from "./constants.js";
import type { BlocklistConfig, BlocklistEntry, BlocklistMatchMode, BlocklistScope } from "./types.js";

/**
 * Generate a random entry identifier for new blocklist rows.
 */
export function newEntryId(): string {
    return Math.random().toString(ID_RANDOM_RADIX).slice(ID_SLICE_START, ID_SLICE_END);
}

/**
 * Create a new blank blocklist entry
 */
export function createNewBlocklistEntry(): BlocklistEntry {
    return {
        id: newEntryId(),
        enabled: true,
        text: "",
        match_mode: DEFAULT_BLOCKLIST_MATCH_MODE,
    };
}

/**
 * Validate and sanitize scope string
 */
export function sanitizeBlocklistScope(rawScope: unknown): BlocklistScope {
    if (rawScope === "contacts" || rawScope === "non_contacts") {
        return rawScope;
    }
    return "everyone";
}

/**
 * Validate and sanitize match mode string
 */
export function sanitizeBlocklistMatchMode(rawMode: unknown): BlocklistMatchMode {
    return rawMode === "regex" ? "regex" : "substring";
}

/**
 * Map raw backend or file payload into sanitized BlocklistConfig
 */
export function mapBlocklistFromApi(raw: unknown): BlocklistConfig {
    const rawObj = (raw && typeof raw === "object" ? raw : {}) as Partial<BlocklistConfig> & {
        entries?: Partial<BlocklistEntry>[];
    };

    const scope = sanitizeBlocklistScope(rawObj.scope);
    const match_peer_fields = Boolean(rawObj.match_peer_fields);
    const match_message = rawObj.match_message !== false;

    const entries: BlocklistEntry[] = Array.isArray(rawObj.entries)
        ? rawObj.entries.map((entry) => ({
              id: entry?.id || newEntryId(),
              enabled: entry?.enabled !== false,
              text: entry?.text || "",
              match_mode: sanitizeBlocklistMatchMode(entry?.match_mode),
          }))
        : [];

    return {
        scope,
        match_peer_fields,
        match_message: match_peer_fields || match_message ? match_message : DEFAULT_BLOCKLIST_MATCH_MESSAGE,
        entries,
    };
}

/**
 * Create default blocklist configuration
 */
export function createDefaultBlocklistConfig(): BlocklistConfig {
    return {
        scope: DEFAULT_BLOCKLIST_SCOPE,
        match_peer_fields: DEFAULT_BLOCKLIST_MATCH_PEER_FIELDS,
        match_message: DEFAULT_BLOCKLIST_MATCH_MESSAGE,
        entries: [],
    };
}

/**
 * Normalize blocklist config for saving to the backend
 */
export function normalizeBlocklistForSave(blocklist: BlocklistConfig): BlocklistConfig {
    const match_peer_fields = Boolean(blocklist.match_peer_fields);
    const match_message = Boolean(blocklist.match_message);
    const targets_ok = match_peer_fields || match_message;

    return {
        scope: sanitizeBlocklistScope(blocklist.scope),
        match_peer_fields: targets_ok ? match_peer_fields : DEFAULT_BLOCKLIST_MATCH_PEER_FIELDS,
        match_message: targets_ok ? match_message : DEFAULT_BLOCKLIST_MATCH_MESSAGE,
        entries: (blocklist.entries || []).map((entry) => ({
            id: entry.id,
            enabled: Boolean(entry.enabled),
            text: String(entry.text || "").trim(),
            match_mode: sanitizeBlocklistMatchMode(entry.match_mode),
        })),
    };
}
