// SPDX-License-Identifier: 0BSD

/**
 * Clamp top-left coordinates for a fixed-position panel so it stays on-screen.
 *
 * @param {number} preferredLeft
 * @param {number} preferredTop
 * @param {number} width
 * @param {number} height
 * @param {{ margin?: number }} [options]
 * @returns {{ left: number, top: number, maxHeight: number | null }}
 */
export function clampFloatingToViewport(preferredLeft, preferredTop, width, height, options = {}) {
    const margin = options.margin ?? 8;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const maxW = Math.max(0, vw - 2 * margin);
    const maxH = Math.max(0, vh - 2 * margin);

    let left = preferredLeft;
    let top = preferredTop;

    if (width <= maxW) {
        left = Math.min(Math.max(margin, left), vw - width - margin);
    } else {
        left = margin;
    }

    let maxHeight = null;
    if (height <= maxH) {
        top = Math.min(Math.max(margin, top), vh - height - margin);
    } else {
        top = margin;
        maxHeight = maxH;
    }

    return { left, top, maxHeight };
}
