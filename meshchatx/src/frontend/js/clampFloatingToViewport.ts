// SPDX-License-Identifier: 0BSD

export type ClampFloatingOptions = {
    margin?: number;
};

export type ClampFloatingResult = {
    left: number;
    top: number;
    maxHeight: number | null;
};

/** Clamp top-left coordinates for a fixed-position panel so it stays on-screen. */
export function clampFloatingToViewport(
    preferredLeft: number,
    preferredTop: number,
    width: number,
    height: number,
    options: ClampFloatingOptions = {}
): ClampFloatingResult {
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

    let maxHeight: number | null = null;
    if (height <= maxH) {
        top = Math.min(Math.max(margin, top), vh - height - margin);
    } else {
        top = margin;
        maxHeight = maxH;
    }

    return { left, top, maxHeight };
}
