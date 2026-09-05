// SPDX-License-Identifier: 0BSD

import type { SieveFolder, SieveMatchMode, SieveRule, SieveRuleAction, SieveRuleScope } from "./types";

/**
 * Generate a random identifier for a new rule
 */
export function newRuleId(): string {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
        return crypto.randomUUID();
    }
    return `r-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

/**
 * Create a fresh default sieve rule
 */
export function createDefaultRule(folders: SieveFolder[] = []): SieveRule {
    return {
        id: newRuleId(),
        enabled: true,
        scope: "everyone",
        terms: [],
        action: "ignore",
        folder_id: folders.length > 0 ? folders[0].id : null,
        match_peer_fields: true,
        match_message: false,
        match_mode: "substring",
    };
}

/**
 * Map a raw rule object received from the API into a typed SieveRule
 */
export function mapRuleFromApi(r: Partial<SieveRule> & { action?: string; id?: string }): SieveRule {
    let action: SieveRuleAction = (r.action as SieveRuleAction) || "ignore";
    if (action === "block") {
        action = "hide";
    }
    const scope: SieveRuleScope = r.scope === "contacts" || r.scope === "non_contacts" ? r.scope : "everyone";
    const matchMode: SieveMatchMode = r.match_mode === "regex" ? "regex" : "substring";

    return {
        id: r.id || newRuleId(),
        enabled: r.enabled !== false,
        scope,
        terms: Array.isArray(r.terms) ? [...r.terms] : [],
        action,
        folder_id: r.folder_id ?? null,
        match_peer_fields: r.match_peer_fields !== false,
        match_message: Boolean(r.match_message),
        match_mode: matchMode,
    };
}

/**
 * Normalize a single rule for the API PUT payload
 */
export function normalizeRuleForSave(r: SieveRule): SieveRule {
    const scope: SieveRuleScope = r.scope === "contacts" || r.scope === "non_contacts" ? r.scope : "everyone";
    const matchPeerFields = r.match_peer_fields !== false;
    const matchMessage = Boolean(r.match_message);
    const targetsOk = matchPeerFields || matchMessage;
    const rawAction = r.action === "block" ? "hide" : r.action;
    const action: SieveRuleAction =
        rawAction === "hide" || rawAction === "folder" || rawAction === "banish" ? rawAction : "ignore";
    const matchMode: SieveMatchMode = r.match_mode === "regex" ? "regex" : "substring";

    return {
        id: r.id,
        enabled: Boolean(r.enabled),
        scope,
        terms: Array.isArray(r.terms) ? [...r.terms] : [],
        action,
        folder_id: action === "folder" ? r.folder_id : null,
        match_peer_fields: targetsOk ? matchPeerFields : true,
        match_message: targetsOk ? matchMessage : false,
        match_mode: matchMode,
    };
}

/**
 * Normalize an array of rules for saving
 */
export function normalizeFiltersForSave(filters: SieveRule[]): SieveRule[] {
    return (filters || []).map(normalizeRuleForSave);
}

/**
 * Parse comma or newline separated terms text into clean strings
 */
export function parseTermsInput(raw: string): string[] {
    return String(raw || "")
        .split(/[\n,]+/)
        .map((s) => s.trim())
        .filter(Boolean);
}

/**
 * Format an array of terms into a newline separated string
 */
export function formatTermsText(terms?: string[]): string {
    return (terms || []).join("\n");
}

/**
 * Move a rule within the filters array by a delta offset
 */
export function reorderRules(filters: SieveRule[], index: number, delta: number): SieveRule[] {
    const targetIndex = index + delta;
    if (targetIndex < 0 || targetIndex >= filters.length) {
        return filters;
    }
    const copy = [...filters];
    const item = copy[index];
    copy[index] = copy[targetIndex];
    copy[targetIndex] = item;
    return copy;
}

/**
 * Ensure folder id matches action requirements
 */
export function ensureValidAction(rule: SieveRule, folders: SieveFolder[] = []): void {
    if (rule.action === "folder" && folders.length > 0 && (rule.folder_id == null || rule.folder_id === 0)) {
        rule.folder_id = folders[0].id;
    }
    if (rule.action !== "folder") {
        rule.folder_id = null;
    }
}

/**
 * Ensure at least one match target stays enabled
 */
export function ensureValidMatchTargets(rule: SieveRule): void {
    if (!rule.match_peer_fields && !rule.match_message) {
        rule.match_peer_fields = true;
    }
}
