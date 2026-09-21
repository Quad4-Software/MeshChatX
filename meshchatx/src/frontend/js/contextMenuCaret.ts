// SPDX-License-Identifier: 0BSD

export type ContextMenuCaret = {
    style: { left: string; top: string };
    borderClass: string;
};

/**
 * Position a caret square on the edge of a fixed popup panel nearest the
 * point that opened it (click origin or trigger center). Returns null when
 * the origin sits inside the panel, so no caret should be rendered.
 * Ported from master's ContextMenuPanel.updateCaret.
 */
export function computeCaret(
    originX: number,
    originY: number,
    left: number,
    top: number,
    width: number,
    height: number
): ContextMenuCaret | null {
    const insideX = originX > left + 4 && originX < left + width - 4;
    const insideY = originY > top + 4 && originY < top + height - 4;
    if (insideX && insideY) {
        return null;
    }

    const size = 5;
    const margin = 12;

    if (originY <= top) {
        const cx = Math.min(Math.max(originX, left + margin), left + width - margin);
        return {
            style: { left: `${cx - size}px`, top: `${top - size}px` },
            borderClass: "border-t border-l",
        };
    }
    if (originY >= top + height) {
        const cx = Math.min(Math.max(originX, left + margin), left + width - margin);
        return {
            style: { left: `${cx - size}px`, top: `${top + height - size}px` },
            borderClass: "border-b border-r",
        };
    }
    if (originX <= left) {
        const cy = Math.min(Math.max(originY, top + margin), top + height - margin);
        return {
            style: { left: `${left - size}px`, top: `${cy - size}px` },
            borderClass: "border-b border-l",
        };
    }
    const cy = Math.min(Math.max(originY, top + margin), top + height - margin);
    return {
        style: { left: `${left + width - size}px`, top: `${cy - size}px` },
        borderClass: "border-t border-r",
    };
}
