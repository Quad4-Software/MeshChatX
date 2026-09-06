// SPDX-License-Identifier: 0BSD

import { calendarDayKeyFromDate } from "./messageTimestampGrouping.js";

const OR_SPLIT_RE = /\s+OR\s+/i;
const DATE_TOKEN_RE = /\bDATE:("([^"]+)"|(\S+))/gi;

export type RelaySearchClause = {
    dateKey: string | null;
    terms: string[];
};

export type RelaySearchMessage = {
    ts?: number | string | null;
    text?: unknown;
    nick?: unknown;
    [key: string]: unknown;
};

export type RelaySearchMember = {
    name?: unknown;
    nickname?: unknown;
    hash?: unknown;
    identity_hash?: unknown;
    [key: string]: unknown;
};

export type RelayDisplayNameFn = (msg?: any) => string;

export function tokenizeSearchTerms(raw: string): string[] {
    const out: string[] = [];
    const re = /[^\s"]+|"([^"]*)"/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(raw)) !== null) {
        const term = (m[1] !== undefined ? m[1] : m[0]).trim();
        if (term) {
            out.push(term);
        }
    }
    return out;
}

/** Parse DATE:today|yesterday|YYYY-MM-DD into a YYYY-MM-DD day key. */
export function parseDateSearchToken(token: string): string | null {
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

export function parseSearchClause(clauseText: string): RelaySearchClause {
    let text = clauseText.trim();
    let dateKey: string | null = null;
    text = text.replace(DATE_TOKEN_RE, (_match, _q, quoted, bare) => {
        const parsed = parseDateSearchToken(quoted !== undefined ? quoted : bare);
        if (parsed) {
            dateKey = parsed;
        }
        return " ";
    });
    return { dateKey, terms: tokenizeSearchTerms(text.trim()) };
}

export function parseRelaySearchQuery(query: string): RelaySearchClause[] {
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

export function messageMatchesSearchClause(
    msg: RelaySearchMessage,
    clause: RelaySearchClause,
    displayNameFn: RelayDisplayNameFn
): boolean {
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

export function filterRelayMessages<T extends RelaySearchMessage>(
    messages: T[],
    query: string,
    displayNameFn: RelayDisplayNameFn
): T[] {
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

export function filterRelayMembers<T extends RelaySearchMember>(members: T[], query: string): T[] {
    const q = (query || "").trim().toLowerCase();
    if (!q || !Array.isArray(members)) {
        return members || [];
    }
    return members.filter((m) => {
        const name = String(m?.name || m?.nickname || "").toLowerCase();
        const hash = String(m?.hash || m?.identity_hash || "").toLowerCase();
        return name.includes(q) || hash.includes(q);
    });
}
