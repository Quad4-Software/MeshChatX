// SPDX-License-Identifier: 0BSD

import { clampFloatingToViewport } from "../../../js/clampFloatingToViewport.js";

export type ReactionPickerPoint = {
    x: number;
    y: number;
};

export type StartReactionPickerDragOptions = {
    event: MouseEvent | TouchEvent;
    getPanel: () => HTMLElement | null | undefined;
    setPosition: (pos: ReactionPickerPoint) => void;
    doc?: Document;
};

type PointerLike = {
    clientX: number;
    clientY: number;
};

function pointerFromEvent(event: MouseEvent | TouchEvent): PointerLike | null {
    const touchList =
        "touches" in event && event.touches && event.touches.length > 0
            ? event.touches
            : "changedTouches" in event && event.changedTouches && event.changedTouches.length > 0
              ? event.changedTouches
              : null;
    const evt = (touchList?.[0] as PointerLike | undefined) || (event as PointerLike);
    if (!evt || typeof evt.clientX !== "number" || typeof evt.clientY !== "number") {
        return null;
    }
    return evt;
}

/** CSS for a dragged reaction picker panel (viewport-fixed top-left). */
export function styleForReactionPickerDragPos(pos: ReactionPickerPoint): string {
    return `position:fixed;left:${pos.x}px;top:${pos.y}px;`;
}

/**
 * Start document-level drag for the reaction picker overlay.
 * Returns a cleanup function, or null when the gesture cannot start.
 */
export function startReactionPickerDrag(options: StartReactionPickerDragOptions): (() => void) | null {
    const doc = options.doc ?? (typeof document !== "undefined" ? document : null);
    if (!doc) {
        return null;
    }
    const evt = pointerFromEvent(options.event);
    const panel = options.getPanel();
    if (!evt || !panel || typeof panel.getBoundingClientRect !== "function") {
        return null;
    }

    const rect = panel.getBoundingClientRect();
    const dragState = {
        startX: evt.clientX,
        startY: evt.clientY,
        originX: rect.left,
        originY: rect.top,
    };

    let cleaned = false;

    const onMove = (moveEvent: Event) => {
        if (cleaned) {
            return;
        }
        const mv = pointerFromEvent(moveEvent as MouseEvent | TouchEvent);
        if (!mv) {
            return;
        }
        const panelEl = options.getPanel();
        if (!panelEl || typeof panelEl.getBoundingClientRect !== "function") {
            return;
        }
        const pr = panelEl.getBoundingClientRect();
        const nx = dragState.originX + (mv.clientX - dragState.startX);
        const ny = dragState.originY + (mv.clientY - dragState.startY);
        const { left, top } = clampFloatingToViewport(nx, ny, pr.width, pr.height);
        options.setPosition({ x: left, y: top });
        if ("cancelable" in moveEvent && moveEvent.cancelable && typeof moveEvent.preventDefault === "function") {
            moveEvent.preventDefault();
        }
    };

    const cleanup = () => {
        if (cleaned) {
            return;
        }
        cleaned = true;
        doc.removeEventListener("mousemove", onMove);
        doc.removeEventListener("mouseup", onUp);
        doc.removeEventListener("touchmove", onMove);
        doc.removeEventListener("touchend", onUp);
        doc.removeEventListener("touchcancel", onUp);
    };

    const onUp = () => {
        cleanup();
    };

    doc.addEventListener("mousemove", onMove);
    doc.addEventListener("mouseup", onUp);
    doc.addEventListener("touchmove", onMove, { passive: false });
    doc.addEventListener("touchend", onUp);
    doc.addEventListener("touchcancel", onUp);

    return cleanup;
}
