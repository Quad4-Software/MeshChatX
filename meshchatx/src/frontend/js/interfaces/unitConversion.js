// SPDX-License-Identifier: 0BSD

/**
 * Human-friendly unit conversion helpers for interface and settings inputs.
 *
 * The backend contract stores bitrates in raw bits per second and intervals
 * in raw seconds. These helpers split a raw value into a (value, unit) pair a
 * human would naturally type, and join the pair back into the raw value, so
 * the stored config never changes shape.
 */

export const BITRATE_UNITS = Object.freeze([
    { id: "bps", label: "bps", multiplier: 1 },
    { id: "kbps", label: "kbps", multiplier: 1000 },
    { id: "Mbps", label: "Mbps", multiplier: 1000000 },
]);

export const DURATION_UNITS = Object.freeze([
    { id: "seconds", label: "seconds", multiplier: 1 },
    { id: "minutes", label: "minutes", multiplier: 60 },
    { id: "hours", label: "hours", multiplier: 3600 },
]);

function toNumber(raw) {
    if (raw === null || raw === undefined || raw === "") {
        return null;
    }
    const num = Number(raw);
    return Number.isFinite(num) ? num : null;
}

function trimFloat(num) {
    // Avoid floating point noise like 57.600000000000001 when dividing.
    return parseFloat(num.toFixed(6));
}

/**
 * Split raw bits per second into the largest unit where the display value
 * stays >= 1. Returns { value, unit } with unit being a BITRATE_UNITS id.
 * Null/invalid input yields a null value and the default kbps unit.
 */
export function splitBitrate(bps) {
    const num = toNumber(bps);
    if (num === null || num <= 0) {
        return { value: null, unit: "kbps" };
    }
    let chosen = BITRATE_UNITS[0];
    for (const unit of BITRATE_UNITS) {
        if (num / unit.multiplier >= 1) {
            chosen = unit;
        }
    }
    return { value: trimFloat(num / chosen.multiplier), unit: chosen.id };
}

/**
 * Join a display value and BITRATE_UNITS id back into raw bits per second.
 * Returns null for empty/invalid input so optional fields stay unset.
 */
export function joinBitrate(value, unitId) {
    const num = toNumber(value);
    if (num === null) {
        return null;
    }
    const unit = BITRATE_UNITS.find((u) => u.id === unitId) || BITRATE_UNITS[0];
    return Math.round(num * unit.multiplier);
}

/**
 * Split raw seconds into the largest whole unit that divides the value
 * evenly, so 720 becomes 12 minutes but 90 stays 90 seconds rather than
 * 1.5 minutes. Sub-minute and fractional values stay in seconds.
 */
export function splitDurationSeconds(seconds) {
    const num = toNumber(seconds);
    if (num === null || num <= 0) {
        return { value: null, unit: "seconds" };
    }
    if (num % 3600 === 0) {
        return { value: num / 3600, unit: "hours" };
    }
    if (num % 60 === 0) {
        return { value: num / 60, unit: "minutes" };
    }
    return { value: trimFloat(num), unit: "seconds" };
}

/**
 * Join a display value and DURATION_UNITS id back into raw seconds.
 * Returns null for empty/invalid input so optional fields stay unset.
 */
export function joinDurationSeconds(value, unitId) {
    const num = toNumber(value);
    if (num === null) {
        return null;
    }
    const unit = DURATION_UNITS.find((u) => u.id === unitId) || DURATION_UNITS[0];
    return trimFloat(num * unit.multiplier);
}
