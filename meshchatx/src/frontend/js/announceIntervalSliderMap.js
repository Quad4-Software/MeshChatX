// SPDX-License-Identifier: 0BSD AND MIT

/** High-resolution slider positions for smooth dragging (minutes 1..1440). */
export const ANNOUNCE_SLIDER_POS_MAX = 2047;

const MIN_MINUTES = 1;
const MAX_MINUTES = 1440;

/**
 * @param {number} pos
 * @returns {number} Announce interval in minutes (1..1440).
 */
export function announceSliderPosToMinutes(pos) {
    const p = Math.max(0, Math.min(ANNOUNCE_SLIDER_POS_MAX, Math.round(Number(pos) || 0)));
    return Math.round(MIN_MINUTES + (p / ANNOUNCE_SLIDER_POS_MAX) * (MAX_MINUTES - MIN_MINUTES));
}

/**
 * @param {number} minutes
 * @returns {number} Slider position 0 .. ANNOUNCE_SLIDER_POS_MAX
 */
export function announceMinutesToSliderPos(minutes) {
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
 * @param {number} minutes
 * @returns {string}
 */
export function formatAnnounceIntervalMinutes(minutes) {
    const m = Math.max(0, Math.round(Number(minutes) || 0));
    if (m === 0) {
        return "0 min";
    }
    const days = Math.floor(m / MINUTES_PER_DAY);
    const hours = Math.floor((m % MINUTES_PER_DAY) / MINUTES_PER_HOUR);
    const mins = m % MINUTES_PER_HOUR;
    const parts = [];
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
 * @param {string} text
 * @returns {number|null} Minutes, or null when the input is not parseable.
 */
export function parseAnnounceIntervalMinutes(text) {
    const s = String(text ?? "")
        .trim()
        .toLowerCase()
        .replace(",", ".");
    if (!s) {
        return null;
    }
    // eslint-disable-next-line security/detect-unsafe-regex -- bounded digit groups, single unit suffix
    if (/^\d+(?:\.\d+)?$/.test(s)) {
        return Math.round(Number(s));
    }
    // eslint-disable-next-line security/detect-unsafe-regex -- bounded number+unit tokens, no nested quantifiers
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
