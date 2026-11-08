/* SPDX-License-Identifier: 0BSD */

let lastTouchStartAt = 0;
if (typeof window !== "undefined") {
    window.addEventListener(
        "touchstart",
        () => {
            lastTouchStartAt = Date.now();
        },
        { capture: true, passive: true }
    );
}

/**
 * True when the contextmenu event was produced by a touch long-press rather
 * than a mouse right-click. pointerType/sourceCapabilities cover Chromium and
 * Android WebView; the touchstart timestamp is a fallback for engines that
 * report neither.
 *
 * @param {Event | null | undefined} event
 * @returns {boolean}
 */
export function isTouchContextMenu(event) {
    if (!event) {
        return false;
    }
    if (event.pointerType === "touch") {
        return true;
    }
    if (event.sourceCapabilities && event.sourceCapabilities.firesTouchEvents) {
        return true;
    }
    return Date.now() - lastTouchStartAt < 1000;
}

/**
 * True when the point under a contextmenu event lands on selectable text.
 * caretRangeFromPoint/caretPositionFromPoint report the nearest text position,
 * which is exactly "is there selectable text under the finger".
 *
 * @param {Event | null | undefined} event
 * @returns {boolean}
 */
export function pointHitsSelectableText(event) {
    const x = event?.clientX;
    const y = event?.clientY;
    if (x == null || y == null || typeof document === "undefined") {
        return false;
    }
    try {
        if (typeof document.caretRangeFromPoint === "function") {
            const range = document.caretRangeFromPoint(x, y);
            return Boolean(range && range.startContainer && range.startContainer.nodeType === 3);
        }
        if (typeof document.caretPositionFromPoint === "function") {
            const pos = document.caretPositionFromPoint(x, y);
            return Boolean(pos && pos.offsetNode && pos.offsetNode.nodeType === 3);
        }
    } catch {
        return false;
    }
    return false;
}

/**
 * True when a contextmenu should not open an app menu so the platform
 * text-selection UI can offer Copy (Android WebView long-press, form fields).
 *
 * @param {Event | null | undefined} event
 * @returns {boolean}
 */
export function preferNativeTextSelectionMenu(event) {
    const target = event?.target;
    if (target && typeof target.closest === "function") {
        if (target.closest("input, textarea, select, [contenteditable='true'], [contenteditable='']")) {
            return true;
        }
    }

    if (typeof window === "undefined" || typeof window.getSelection !== "function") {
        return false;
    }

    const selection = window.getSelection();
    if (!selection || selection.rangeCount < 1 || selection.isCollapsed) {
        return false;
    }

    const text = selection.toString();
    if (!text || text.length < 1) {
        return false;
    }

    if (!target) {
        return true;
    }

    try {
        const range = selection.getRangeAt(0);
        if (typeof range.intersectsNode === "function") {
            return range.intersectsNode(target);
        }
    } catch {
        return true;
    }

    return true;
}

/**
 * Call preventDefault (and optional stopPropagation) then run openFn when an
 * app context menu should win. Returns false when native selection/copy wins.
 *
 * @param {Event} event
 * @param {(event: Event) => void} openFn
 * @param {{ stopPropagation?: boolean }} [options]
 * @returns {boolean}
 */
export function openAppContextMenuUnlessTextSelection(event, openFn, options = {}) {
    if (!shouldOpenCustomContextMenu(event)) {
        return false;
    }
    if (event && typeof event.preventDefault === "function") {
        event.preventDefault();
    }
    if (options.stopPropagation && event && typeof event.stopPropagation === "function") {
        event.stopPropagation();
    }
    openFn(event);
    return true;
}

/**
 * Single gate every app contextmenu handler should consult before
 * preventDefault + opening a custom menu:
 *  - an existing selection intersecting the target wins (native Copy);
 *  - a touch long-press over selectable text wins so text selection and the
 *    OS copy/paste toolbar keep working (the 3-dot button stays the touch
 *    path to app menus);
 *  - everything else (mouse right-click, long-press on non-text chrome)
 *    opens the app menu.
 *
 * @param {Event | null | undefined} event
 * @returns {boolean}
 */
export function shouldOpenCustomContextMenu(event) {
    if (preferNativeTextSelectionMenu(event)) {
        return false;
    }
    if (isTouchContextMenu(event) && pointHitsSelectableText(event)) {
        return false;
    }
    return true;
}
