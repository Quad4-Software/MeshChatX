// SPDX-License-Identifier: 0BSD

/** High-resolution slider positions for smooth dragging (minutes 1..1440). */
export const ANNOUNCE_SLIDER_POS_MAX = 2047;

const MIN_MINUTES = 1;
const MAX_MINUTES = 1440;

/** Announce interval in minutes (1..1440). */
export function announceSliderPosToMinutes(pos: number): number {
    const p = Math.max(0, Math.min(ANNOUNCE_SLIDER_POS_MAX, Math.round(Number(pos) || 0)));
    return Math.round(MIN_MINUTES + (p / ANNOUNCE_SLIDER_POS_MAX) * (MAX_MINUTES - MIN_MINUTES));
}

/** Slider position 0 .. ANNOUNCE_SLIDER_POS_MAX */
export function announceMinutesToSliderPos(minutes: number): number {
    const raw = Number(minutes);
    if (Number.isFinite(raw) && raw === 0) {
        return 0;
    }
    const m = Math.max(MIN_MINUTES, Math.min(MAX_MINUTES, Math.round(Number(minutes) || MIN_MINUTES)));
    return Math.round(((m - MIN_MINUTES) / (MAX_MINUTES - MIN_MINUTES)) * ANNOUNCE_SLIDER_POS_MAX);
}

const MINUTES_PER_HOUR = 60;
const MINUTES_PER_DAY = 1440;

/**
 * Human readable interval, e.g. "45 min", "6 h", "1 h 30 min", "1 d".
 */
export function formatAnnounceIntervalMinutes(minutes: number): string {
    const m = Math.max(0, Math.round(Number(minutes) || 0));
    if (m === 0) {
        return "0 min";
    }
    const days = Math.floor(m / MINUTES_PER_DAY);
    const hours = Math.floor((m % MINUTES_PER_DAY) / MINUTES_PER_HOUR);
    const mins = m % MINUTES_PER_HOUR;
    const parts: string[] = [];
    if (days) {
        parts.push(`${days} d`);
    }
    if (hours) {
        parts.push(`${hours} h`);
    }
    if (mins) {
        parts.push(`${mins} min`);
    }
    return parts.join(" ");
}

/**
 * Parse a typed interval back to minutes. Accepts a bare number (minutes)
 * or unit-suffixed parts like "6h", "1h 30m", "45min", "1d".
 * Returns minutes, or null when the input is not parseable.
 */
export function parseAnnounceIntervalMinutes(text: string | null | undefined): number | null {
    const raw = String(text ?? "")
        .trim()
        .toLowerCase();
    // Comma is ambiguous: "1,5" is a decimal comma but "1,440" is thousands
    // grouping. Only rewrite it as a decimal point when it is not grouped
    // in digit triads, otherwise strip the separators outright.
    // eslint-disable-next-line security/detect-unsafe-regex -- bounded digit groups only
    const s = /^\d{1,3}(,\d{3})+$/.test(raw) ? raw.replace(/,/g, "") : raw.replace(",", ".");
    if (!s) {
        return null;
    }
    // eslint-disable-next-line security/detect-unsafe-regex -- bounded digits and optional decimal only
    if (/^\d+(?:\.\d+)?$/.test(s)) {
        return Math.round(Number(s));
    }
    // eslint-disable-next-line security/detect-unsafe-regex -- linear scan, no nested quantifiers
    const re = /(\d+(?:\.\d+)?)\s*(d|h|m(?:in)?)/g;
    let matched = "";
    let total = 0;
    for (const part of s.matchAll(re)) {
        matched += part[0];
        const value = Number(part[1]);
        const unit = part[2];
        if (unit === "d") {
            total += value * MINUTES_PER_DAY;
        } else if (unit === "h") {
            total += value * MINUTES_PER_HOUR;
        } else {
            total += value;
        }
    }
    if (!matched || matched.replace(/\s+/g, "") !== s.replace(/\s+/g, "")) {
        return null;
    }
    return Math.round(total);
}
