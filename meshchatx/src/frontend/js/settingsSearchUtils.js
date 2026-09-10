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
 * Split a camelCase or PascalCase id into lowercase words.
 * @param {string} sectionKey
 * @returns {string}
 */
export function camelCaseToSearchWords(sectionKey) {
    return String(sectionKey || "")
        .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
        .replace(/_/g, " ")
        .toLowerCase()
        .trim();
}

/**
 * @param {string} folded
 * @returns {string}
 */
function replaceNonAlnumWithSpace(folded) {
    try {
        return folded.replace(/[^\p{L}\p{N}]+/gu, " ");
    } catch {
        return folded.replace(/[\s\-_/,.:;+|]+/g, " ");
    }
}

/**
 * @param {string} normalizedTrimmed
 * @returns {string[]}
 */
export function tokenizeSettingsQuery(normalizedTrimmed) {
    if (!normalizedTrimmed) return [];
    return replaceNonAlnumWithSpace(foldForSearch(normalizedTrimmed))
        .split(/\s+/)
        .filter((t) => t.length > 0);
}

/**
 * Short tokens (1-2 chars) must be whole words so "me" does not hit "theme".
 * Longer tokens match as substrings, including a spaceless compact haystack
 * so "darkmode" hits "dark mode".
 *
 * @param {string} tok
 * @param {string} haystack
 * @param {string} compactHaystack
 * @returns {boolean}
 */
export function tokenMatchesHaystack(tok, haystack, compactHaystack) {
    if (!tok) return true;
    if (tok.length <= 2) {
        return ` ${haystack} `.includes(` ${tok} `);
    }
    return haystack.includes(tok) || compactHaystack.includes(tok);
}

/**
 * @param {string} text
 * @param {(key: string) => string} translateFn
 * @returns {string}
 */
function resolveSnippet(text, translateFn) {
    if (!text) return "";
    const s = String(text);
    if (s.startsWith("=")) {
        return foldForSearch(s.slice(1));
    }
    const content = s.includes(".") ? translateFn(s) : s;
    return foldForSearch(content);
}

/**
 * @param {string[]} texts
 * @param {(key: string) => string} translateFn
 * @returns {{ haystack: string, compactHaystack: string }}
 */
export function buildSettingsSearchHaystack(texts, translateFn) {
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
    const { haystack, compactHaystack } = buildSettingsSearchHaystack(texts, translateFn);
    if (!haystack) return false;
    return tokens.every((tok) => tokenMatchesHaystack(tok, haystack, compactHaystack));
}

/**
 * Bounded Levenshtein check with early exit.
 * @param {string} a
 * @param {string} b
 * @param {number} limit
 * @returns {boolean}
 */
function editDistanceWithin(a, b, limit) {
    if (Math.abs(a.length - b.length) > limit) return false;
    let prev = Array.from({ length: b.length + 1 }, (_, i) => i);
    for (let i = 1; i <= a.length; i++) {
        const cur = [i];
        let rowMin = i;
        for (let j = 1; j <= b.length; j++) {
            const cost = a[i - 1] === b[j - 1] ? 0 : 1;
            cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost);
            if (cur[j] < rowMin) rowMin = cur[j];
        }
        if (rowMin > limit) return false;
        prev = cur;
    }
    return prev[b.length] <= limit;
}

/**
 * Typo-tolerant variant: every token must match, but tokens of 4+ characters
 * may be one edit away from a haystack word (two edits for 8+ chars). Used as
 * a fallback tier when strict matching finds nothing, so queries like
 * "mesages" still surface the messages settings.
 *
 * @param {string[]} texts
 * @param {(key: string) => string} translateFn
 * @param {string} rawQuery
 * @returns {boolean}
 */
export function matchesSettingSearchFuzzy(texts, translateFn, rawQuery) {
    const tokens = tokenizeSettingsQuery(normalizeSearchString(rawQuery));
    if (!tokens.length) return true;
    const { haystack, compactHaystack } = buildSettingsSearchHaystack(texts, translateFn);
    if (!haystack) return false;
    const words = haystack.split(" ").filter(Boolean);
    return tokens.every((tok) => {
        if (tokenMatchesHaystack(tok, haystack, compactHaystack)) {
            return true;
        }
        if (tok.length < 4) {
            return false;
        }
        const limit = tok.length >= 8 ? 2 : 1;
        return words.some((word) => editDistanceWithin(tok, word, limit));
    });
}
