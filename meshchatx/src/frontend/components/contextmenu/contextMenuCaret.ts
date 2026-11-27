// SPDX-License-Identifier: 0BSD

export interface CaretPlacement {
    style: Record<string, string> | null;
    borderClass: string;
}

/**
 * Pure geometry for the context menu caret. The caret sits on the panel edge
 * nearest the origin point, clamped off the rounded corners so it stays on
 * the straight part of the edge.
 */
export function computeCaretPlacement(
    ox: number,
    oy: number,
    left: number,
    top: number,
    width: number,
    height: number
): CaretPlacement {
    // An anchor inside or on the panel edge has nothing to point at.
    const insideX = ox >= left && ox <= left + width;
    const insideY = oy >= top && oy <= top + height;
    if (insideX && insideY) {
        return { style: null, borderClass: "border-t border-l" };
    }
    const size = 5;
    // Keep the caret on the straight part of the edge: rounded-xl
    // corners span 12px and the caret is 10px wide.
    const margin = 18;
    if (oy <= top) {
        const cx = Math.min(Math.max(ox, left + margin), left + width - margin);
        return { style: { left: `${cx - size}px`, top: `${top - size}px` }, borderClass: "border-t border-l" };
    }
    if (oy >= top + height) {
        const cx = Math.min(Math.max(ox, left + margin), left + width - margin);
        return {
            style: { left: `${cx - size}px`, top: `${top + height - size}px` },
            borderClass: "border-b border-r",
        };
    }
    if (ox <= left) {
        const cy = Math.min(Math.max(oy, top + margin), top + height - margin);
        return { style: { left: `${left - size}px`, top: `${cy - size}px` }, borderClass: "border-b border-l" };
    }
    const cy = Math.min(Math.max(oy, top + margin), top + height - margin);
    return { style: { left: `${left + width - size}px`, top: `${cy - size}px` }, borderClass: "border-t border-r" };
}
