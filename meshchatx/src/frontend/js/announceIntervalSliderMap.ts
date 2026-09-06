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
