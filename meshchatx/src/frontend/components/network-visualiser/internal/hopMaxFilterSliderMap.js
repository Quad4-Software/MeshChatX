// SPDX-License-Identifier: 0BSD AND MIT

/** Rightmost slider index: no hop limit (show all paths). */
export const HOP_SLIDER_POS_ALL = 2047;

const LOW_MAX_POS = 1599;
const TRAN_POS = 1600;
const HIGH_END_POS = 2046;

/**
 * @param {number} pos
 * @returns {number|null} Inclusive max hops, or null when unlimited.
 */
export function hopSliderPosToMaxHops(pos) {
    const p = Math.round(Number(pos));
    if (!Number.isFinite(p) || p >= HOP_SLIDER_POS_ALL) return null;
    if (p <= LOW_MAX_POS) {
        return Math.min(32, Math.round((p / LOW_MAX_POS) * 32));
    }
    if (p >= HIGH_END_POS) return 128;
    const span = HIGH_END_POS - TRAN_POS;
    const frac = span > 0 ? (p - TRAN_POS) / span : 1;
    return Math.min(128, Math.max(33, Math.round(33 + frac * (128 - 33))));
}

/**
 * @param {number|null|undefined} maxHops null = unlimited
 * @returns {number} Slider position 0 .. HOP_SLIDER_POS_ALL
 */
export function hopMaxHopsToSliderPos(maxHops) {
    if (maxHops === null || maxHops === undefined) return HOP_SLIDER_POS_ALL;
    const h = Math.max(0, Math.min(128, Math.round(Number(maxHops))));
    if (h <= 32) {
        return Math.round((h / 32) * LOW_MAX_POS);
    }
    const span = HIGH_END_POS - TRAN_POS;
    return Math.min(HIGH_END_POS, TRAN_POS + Math.round(((h - 33) / (128 - 33)) * span));
}
