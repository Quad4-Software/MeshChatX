// SPDX-License-Identifier: 0BSD

const ZW_RE = /[\u200B-\u200D\uFEFF]/g;

export type SettingsTranslateFn = (key: string) => string;

export type SettingsSearchHaystack = {
    haystack: string;
    compactHaystack: string;
};

export function normalizeSearchString(raw: unknown): string {
    if (raw == null) return "";
    const s = String(raw).replace(ZW_RE, "");
    return s.trim();
}

/**
 * Lowercase, strip combining marks for loose matching, normalize sharp s for German keyboards.
 */
export function foldForSearch(str: string): string {
    if (!str) return "";
    let out = String(str).toLowerCase();
    try {
        out = out.normalize("NFD").replace(/\p{M}/gu, "");
    } catch {
        // Unicode property escapes unsupported in very old runtimes
    }
    return out.replace(/\u00df/g, "ss");
}

/** Split a camelCase or PascalCase id into lowercase words. */
export function camelCaseToSearchWords(sectionKey: string): string {
    return String(sectionKey || "")
        .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
        .replace(/_/g, " ")
        .toLowerCase()
        .trim();
}

function replaceNonAlnumWithSpace(folded: string): string {
    try {
        return folded.replace(/[^\p{L}\p{N}]+/gu, " ");
    } catch {
        return folded.replace(/[\s\-_/,.:;+|]+/g, " ");
    }
}

export function tokenizeSettingsQuery(normalizedTrimmed: string): string[] {
    if (!normalizedTrimmed) return [];
    return replaceNonAlnumWithSpace(foldForSearch(normalizedTrimmed))
        .split(/\s+/)
        .filter((t) => t.length > 0);
}

/**
 * Short tokens (1-2 chars) must be whole words so "me" does not hit "theme".
 * Longer tokens match as substrings, including a spaceless compact haystack
 * so "darkmode" hits "dark mode".
 */
export function tokenMatchesHaystack(tok: string, haystack: string, compactHaystack: string): boolean {
    if (!tok) return true;
    if (tok.length <= 2) {
        return ` ${haystack} `.includes(` ${tok} `);
    }
    return haystack.includes(tok) || compactHaystack.includes(tok);
}

function resolveSnippet(text: string, translateFn: SettingsTranslateFn): string {
    if (!text) return "";
    const s = String(text);
    if (s.startsWith("=")) {
        return foldForSearch(s.slice(1));
    }
    const content = s.includes(".") ? translateFn(s) : s;
    return foldForSearch(content);
}

export function buildSettingsSearchHaystack(texts: string[], translateFn: SettingsTranslateFn): SettingsSearchHaystack {
    const folded = texts
        .map((t) => resolveSnippet(t, translateFn))
        .filter(Boolean)
        .join(" ");
    const haystack = replaceNonAlnumWithSpace(folded).replace(/\s+/g, " ").trim();
    return {
        haystack,
        compactHaystack: haystack.replace(/\s+/g, ""),
    };
}

/**
 * Settings section search: empty query shows all. Otherwise every token from
 * the query (split on whitespace and punctuation) must appear in the combined
 * translated keyword haystack.
 * texts may be raw strings or i18n keys (keys contain a dot).
 */
export function matchesSettingSearch(texts: string[], translateFn: SettingsTranslateFn, rawQuery: string): boolean {
    const normalized = normalizeSearchString(rawQuery);
    if (!normalized) return true;
    const tokens = tokenizeSettingsQuery(normalized);
    if (!tokens.length) return true;
    const { haystack, compactHaystack } = buildSettingsSearchHaystack(texts, translateFn);
    if (!haystack) return false;
    return tokens.every((tok) => tokenMatchesHaystack(tok, haystack, compactHaystack));
}
