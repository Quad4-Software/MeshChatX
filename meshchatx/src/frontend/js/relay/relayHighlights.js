// SPDX-License-Identifier: 0BSD

/**
 * Custom highlight-word matching for relay chat. Words match whole-token and
 * case-insensitively so "uucp" does not fire inside "uucpd". Matching is a
 * pure client-side view concern; nothing is transmitted to peers.
 */

const WORD_CHARS = "\\p{L}\\p{N}_";
const regexCache = new Map();
const REGEX_CACHE_MAX = 128;

function wordRegex(word) {
    const w = String(word || "").trim();
    if (!w) {
        return null;
    }
    const key = w.toLowerCase();
    const hit = regexCache.get(key);
    if (hit) {
        return hit;
    }
    const esc = w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    // eslint-disable-next-line security/detect-non-literal-regexp -- word is user config, escaped above
    const re = new RegExp(`(^|[^${WORD_CHARS}])${esc}(?![${WORD_CHARS}])`, "iu");
    regexCache.set(key, re);
    if (regexCache.size > REGEX_CACHE_MAX) {
        regexCache.delete(regexCache.keys().next().value);
    }
    return re;
}

export function relayTextMatchesWords(text, words) {
    if (typeof text !== "string" || !text || !Array.isArray(words) || words.length === 0) {
        return false;
    }
    for (const w of words) {
        const re = wordRegex(w);
        if (re && re.test(text)) {
            return true;
        }
    }
    return false;
}

export function normalizeHighlightWordInput(input) {
    const w = String(input || "")
        .trim()
        .replace(/\s+/g, " ");
    return w || "";
}
