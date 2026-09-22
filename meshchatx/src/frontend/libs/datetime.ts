// SPDX-License-Identifier: 0BSD

/**
 * Local datetime helpers for MeshChatX.
 * formatDate supports a frozen token subset. fromNow uses a frozen English golden table.
 */

export const MONTHS_SHORT = Object.freeze([
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]);

/** Tokens accepted by formatDate. Unknown tokens stay literal. */
export const SUPPORTED_FORMAT_TOKENS = Object.freeze([
    "YYYY",
    "MMM",
    "MM",
    "M",
    "DD",
    "D",
    "HH",
    "H",
    "hh",
    "h",
    "mm",
    "A",
    "a",
]);

export type FormatToken = (typeof SUPPORTED_FORMAT_TOKENS)[number];

const TOKEN_RE = /YYYY|MMM|MM|M|DD|D|HH|H|hh|h|mm|A|a/g;

export type FromNowFixedThreshold = Readonly<{
    limitSec: number;
    past: string;
    future: string;
}>;

export type FromNowUnitThreshold = Readonly<{
    limitSec: number;
    unitSec: number;
    unit: string;
}>;

export type FromNowThreshold = FromNowFixedThreshold | FromNowUnitThreshold;

/**
 * Frozen relative-time thresholds. Do not change without updating golden tests.
 * limitSec is inclusive upper bound for the absolute second delta.
 */
export const FROM_NOW_THRESHOLDS: readonly FromNowThreshold[] = Object.freeze([
    Object.freeze({ limitSec: 44, past: "a few seconds ago", future: "in a few seconds" }),
    Object.freeze({ limitSec: 89, past: "a minute ago", future: "in a minute" }),
    Object.freeze({ limitSec: 44 * 60, unitSec: 60, unit: "minute" }),
    Object.freeze({ limitSec: 89 * 60, past: "an hour ago", future: "in an hour" }),
    Object.freeze({ limitSec: 21 * 3600, unitSec: 3600, unit: "hour" }),
    Object.freeze({ limitSec: 35 * 3600, past: "a day ago", future: "in a day" }),
    Object.freeze({ limitSec: 25 * 86400, unitSec: 86400, unit: "day" }),
    Object.freeze({ limitSec: 45 * 86400, past: "a month ago", future: "in a month" }),
    Object.freeze({ limitSec: 10 * 30 * 86400, unitSec: 30 * 86400, unit: "month" }),
    Object.freeze({ limitSec: 17 * 365 * 86400, past: "a year ago", future: "in a year" }),
    Object.freeze({ limitSec: Number.POSITIVE_INFINITY, unitSec: 365 * 86400, unit: "year" }),
]);

export type FromNowGoldenEntry = readonly [deltaSec: number, expectedPast: string, expectedFuture: string];

/**
 * Golden samples for fromNow. Kept next to the implementation so drift is obvious.
 * Each entry: [deltaSec, expectedPast, expectedFuture]
 */
export const FROM_NOW_GOLDEN: readonly FromNowGoldenEntry[] = Object.freeze([
    Object.freeze([0, "a few seconds ago", "a few seconds ago"] as const),
    Object.freeze([1, "a few seconds ago", "in a few seconds"] as const),
    Object.freeze([44, "a few seconds ago", "in a few seconds"] as const),
    Object.freeze([45, "a minute ago", "in a minute"] as const),
    Object.freeze([89, "a minute ago", "in a minute"] as const),
    Object.freeze([90, "2 minutes ago", "in 2 minutes"] as const),
    Object.freeze([120, "2 minutes ago", "in 2 minutes"] as const),
    Object.freeze([44 * 60, "44 minutes ago", "in 44 minutes"] as const),
    Object.freeze([45 * 60, "an hour ago", "in an hour"] as const),
    Object.freeze([89 * 60, "an hour ago", "in an hour"] as const),
    Object.freeze([90 * 60, "2 hours ago", "in 2 hours"] as const),
    Object.freeze([21 * 3600, "21 hours ago", "in 21 hours"] as const),
    Object.freeze([22 * 3600, "a day ago", "in a day"] as const),
    Object.freeze([35 * 3600, "a day ago", "in a day"] as const),
    Object.freeze([36 * 3600, "2 days ago", "in 2 days"] as const),
    Object.freeze([2 * 86400, "2 days ago", "in 2 days"] as const),
    Object.freeze([25 * 86400, "25 days ago", "in 25 days"] as const),
    Object.freeze([26 * 86400, "a month ago", "in a month"] as const),
    Object.freeze([45 * 86400, "a month ago", "in a month"] as const),
    Object.freeze([46 * 86400, "2 months ago", "in 2 months"] as const),
    Object.freeze([10 * 30 * 86400, "10 months ago", "in 10 months"] as const),
    Object.freeze([11 * 30 * 86400, "a year ago", "in a year"] as const),
    Object.freeze([17 * 365 * 86400, "a year ago", "in a year"] as const),
    Object.freeze([18 * 365 * 86400, "18 years ago", "in 18 years"] as const),
]);
export function toDate(input: unknown): Date | null {
    if (input == null || input === "") {
        return null;
    }
    if (input instanceof Date) {
        const t = input.getTime();
        return Number.isFinite(t) ? input : null;
    }
    if (typeof input === "number") {
        if (!Number.isFinite(input)) {
            return null;
        }
        const d = new Date(input);
        return Number.isFinite(d.getTime()) ? d : null;
    }
    if (typeof input === "string") {
        const d = new Date(input);
        return Number.isFinite(d.getTime()) ? d : null;
    }
    return null;
}

function formatToken(date: Date, token: string): string {
    const month = date.getMonth();
    const day = date.getDate();
    const hours24 = date.getHours();
    const minutes = date.getMinutes();
    const year = date.getFullYear();
    const hours12 = hours24 % 12 || 12;
    const ampm = hours24 < 12 ? "AM" : "PM";

    switch (token) {
        case "YYYY":
            return String(year).padStart(4, "0");
        case "MMM":
            return MONTHS_SHORT[month] ?? token;
        case "MM":
            return String(month + 1).padStart(2, "0");
        case "M":
            return String(month + 1);
        case "DD":
            return String(day).padStart(2, "0");
        case "D":
            return String(day);
        case "HH":
            return String(hours24).padStart(2, "0");
        case "H":
            return String(hours24);
        case "hh":
            return String(hours12).padStart(2, "0");
        case "h":
            return String(hours12);
        case "mm":
            return String(minutes).padStart(2, "0");
        case "A":
            return ampm;
        case "a":
            return ampm.toLowerCase();
        default:
            return token;
    }
}

/**
 * True when every format token in pattern is in SUPPORTED_FORMAT_TOKENS.
 * Literals and punctuation are ignored.
 */
export function isSupportedFormatPattern(pattern: unknown): boolean {
    if (typeof pattern !== "string" || pattern.length === 0) {
        return false;
    }
    const matches = pattern.match(TOKEN_RE);
    if (!matches) {
        return true;
    }
    const supported: readonly string[] = SUPPORTED_FORMAT_TOKENS;
    return matches.every((token) => supported.includes(token));
}

/**
 * Format a date with the frozen token subset.
 * Supported: YYYY MMM MM M DD D HH H hh h mm A a
 */
export function formatDate(input: unknown, pattern: unknown): string {
    const date = toDate(input);
    if (!date || typeof pattern !== "string" || pattern.length === 0) {
        return "";
    }
    return pattern.replace(TOKEN_RE, (token) => formatToken(date, token));
}

function pluralUnitLabel(unit: string, n: number, isFuture: boolean): string {
    const word = n === 1 ? unit : `${unit}s`;
    return isFuture ? `in ${n} ${word}` : `${n} ${word} ago`;
}

/**
 * Pure relative label from absolute seconds and polarity.
 */
export function relativeLabel(absSec: number, isFuture: boolean): string {
    const sec = Math.max(0, Math.round(Number(absSec) || 0));
    for (const row of FROM_NOW_THRESHOLDS) {
        if (sec > row.limitSec) {
            continue;
        }
        if ("unit" in row && row.unit) {
            const n = Math.max(1, Math.round(sec / row.unitSec));
            return pluralUnitLabel(row.unit, n, isFuture);
        }
        if (sec === 0) {
            return "past" in row ? row.past : "";
        }
        return isFuture ? ("future" in row ? row.future : "") : "past" in row ? row.past : "";
    }
    // FROM_NOW_THRESHOLDS always ends at Infinity. Kept as a safety net.
    return isFuture ? "in a few seconds" : "a few seconds ago";
}

/**
 * Relative time string from input toward now (default Date.now()).
 */
export function fromNow(input: unknown, nowInput: unknown = Date.now()): string {
    const date = toDate(input);
    const now = toDate(nowInput);
    if (!date || !now) {
        return "";
    }
    const diffMs = date.getTime() - now.getTime();
    const absSec = Math.round(Math.abs(diffMs) / 1000);
    const isFuture = diffMs > 0;
    return relativeLabel(absSec, isFuture);
}

export interface MeshDateHelper {
    format(pattern: unknown): string;
    fromNow(nowInput?: unknown): string;
    toDate(): Date | null;
}

/**
 * dayjs-like helper for call sites that previously did dayjs(x).format / .fromNow.
 */
export function meshDate(input: unknown): MeshDateHelper {
    return {
        format(pattern) {
            return formatDate(input, pattern);
        },
        fromNow(nowInput) {
            return fromNow(input, nowInput);
        },
        toDate() {
            return toDate(input);
        },
    };
}
