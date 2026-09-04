/* SPDX-License-Identifier: 0BSD */

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
    if (preferNativeTextSelectionMenu(event)) {
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
