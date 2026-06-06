// SPDX-License-Identifier: 0BSD AND MIT

import { calendarDayKeyFromDate } from "./messageTimestampGrouping.js";

const OR_SPLIT_RE = /\s+OR\s+/i;
const DATE_TOKEN_RE = /\bDATE:("([^"]+)"|(\S+))/gi;

/**
 * @param {string} raw
 * @returns {string[]}
 */
export function tokenizeSearchTerms(raw) {
    const out = [];
    const re = /[^\s"]+|"([^"]*)"/g;
    let m;
    while ((m = re.exec(raw)) !== null) {
        const term = (m[1] !== undefined ? m[1] : m[0]).trim();
        if (term) {
            out.push(term);
        }
    }
    return out;
}

/**
 * @param {string} token
 * @returns {string | null} YYYY-MM-DD day key
 */
export function parseDateSearchToken(token) {
    if (!token || typeof token !== "string") {
        return null;
    }
    const t = token.trim().toLowerCase();
    const today = new Date();
    if (t === "today") {
        return calendarDayKeyFromDate(today);
    }
    if (t === "yesterday") {
        const y = new Date(today);
        y.setDate(y.getDate() - 1);
        return calendarDayKeyFromDate(y);
    }
    const iso = /^(\d{4})-(\d{2})-(\d{2})$/.exec(token.trim());
    if (iso) {
        const d = new Date(parseInt(iso[1], 10), parseInt(iso[2], 10) - 1, parseInt(iso[3], 10));
        if (!Number.isNaN(d.getTime())) {
            return calendarDayKeyFromDate(d);
        }
    }
    return null;
}

/**
 * @param {string} clauseText
 * @returns {{ dateKey: string | null, terms: string[] }}
 */
export function parseSearchClause(clauseText) {
    let text = clauseText.trim();
    let dateKey = null;
    text = text.replace(DATE_TOKEN_RE, (_, _q, quoted, bare) => {
        const parsed = parseDateSearchToken(quoted !== undefined ? quoted : bare);
        if (parsed) {
            dateKey = parsed;
        }
        return " ";
    });
    return { dateKey, terms: tokenizeSearchTerms(text.trim()) };
}

/**
 * @param {string} query
 * @returns {{ dateKey: string | null, terms: string[] }[]}
 */
export function parseRelaySearchQuery(query) {
    const trimmed = (query || "").trim();
    if (!trimmed) {
        return [];
    }
    const parts = trimmed
        .split(OR_SPLIT_RE)
        .map((p) => p.trim())
        .filter(Boolean);
    return parts.map(parseSearchClause);
}

/**
 * @param {object} msg
 * @param {{ dateKey: string | null, terms: string[] }} clause
 * @param {(msg: object) => string} displayNameFn
 * @returns {boolean}
 */
export function messageMatchesSearchClause(msg, clause, displayNameFn) {
    if (clause.dateKey) {
        const ts = msg?.ts;
        if (ts == null) {
            return false;
        }
        const ms = typeof ts === "number" ? ts : Number(ts);
        const d = new Date(ms);
        if (Number.isNaN(d.getTime())) {
            return false;
        }
        if (calendarDayKeyFromDate(d) !== clause.dateKey) {
            return false;
        }
    }
    if (!clause.terms.length) {
        return Boolean(clause.dateKey);
    }
    const hay = [msg?.text, msg?.nick, displayNameFn(msg)].filter(Boolean).join(" ").toLowerCase();
    return clause.terms.every((term) => hay.includes(term.toLowerCase()));
}

/**
 * @param {object[]} messages
 * @param {string} query
 * @param {(msg: object) => string} displayNameFn
 * @returns {object[]}
 */
export function filterRelayMessages(messages, query, displayNameFn) {
    const trimmed = (query || "").trim();
    if (!trimmed || !Array.isArray(messages)) {
        return [];
    }
    const clauses = parseRelaySearchQuery(trimmed);
    if (!clauses.length) {
        return [];
    }
    return messages.filter((msg) => clauses.some((clause) => messageMatchesSearchClause(msg, clause, displayNameFn)));
}

/**
 * @param {object[]} members
 * @param {string} query
 * @returns {object[]}
 */
export function filterRelayMembers(members, query) {
    const q = (query || "").trim().toLowerCase();
    if (!q || !Array.isArray(members)) {
        return members || [];
    }
    return members.filter((m) => {
        const name = (m?.name || "").toLowerCase();
        const hash = (m?.hash || "").toLowerCase();
        return name.includes(q) || hash.includes(q);
    });
}
