// SPDX-License-Identifier: 0BSD AND MIT

const ZW_RE = /[\u200B-\u200D\uFEFF]/g;

/**
 * @param {unknown} raw
 * @returns {string}
 */
export function normalizeSearchString(raw) {
    if (raw == null) return "";
    const s = String(raw).replace(ZW_RE, "");
    return s.trim();
}

/**
 * Lowercase, strip combining marks for loose matching, normalize sharp s for German keyboards.
 * @param {string} str
 * @returns {string}
 */
export function foldForSearch(str) {
    if (!str) return "";
    let out = String(str).toLowerCase();
    try {
        out = out.normalize("NFD").replace(/\p{M}/gu, "");
    } catch {
        // Unicode property escapes unsupported in very old runtimes
    }
    return out.replace(/\u00df/g, "ss");
}

/**
 * @param {string} normalizedTrimmed
 * @returns {string[]}
 */
export function tokenizeSettingsQuery(normalizedTrimmed) {
    if (!normalizedTrimmed) return [];
    return normalizedTrimmed
        .toLowerCase()
        .split(/\s+/)
        .map((t) => foldForSearch(t))
        .filter((t) => t.length > 0);
}

/**
 * @param {string} text
 * @param {(key: string) => string} translateFn
 * @returns {string}
 */
function resolveSnippet(text, translateFn) {
    if (!text) return "";
    const s = String(text);
    const content = s.includes(".") ? translateFn(s) : s;
    return foldForSearch(content);
}

/**
 * Settings section search: empty query shows all; otherwise every whitespace-separated
 * token must appear somewhere in the combined (translated) keyword haystack.
 *
 * @param {string[]} texts raw strings or i18n keys (keys contain a dot)
 * @param {(key: string) => string} translateFn
 * @param {string} rawQuery
 * @returns {boolean}
 */
export function matchesSettingSearch(texts, translateFn, rawQuery) {
    const normalized = normalizeSearchString(rawQuery);
    if (!normalized) return true;
    const tokens = tokenizeSettingsQuery(normalized);
    if (!tokens.length) return true;
    const haystack = texts
        .map((t) => resolveSnippet(t, translateFn))
        .filter(Boolean)
        .join(" ");
    if (!haystack) return false;
    return tokens.every((tok) => haystack.includes(tok));
}
