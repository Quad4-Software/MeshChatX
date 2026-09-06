/* SPDX-License-Identifier: 0BSD */

export type OpenAppContextMenuOptions = {
    stopPropagation?: boolean;
};

/**
 * True when a contextmenu should not open an app menu so the platform
 * text-selection UI can offer Copy (Android WebView long-press, form fields).
 */
export function preferNativeTextSelectionMenu(event: Event | null | undefined): boolean {
    const target = event?.target as
        (EventTarget & { closest?: (selector: string) => Element | null }) | null | undefined;
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
        if (typeof range.intersectsNode === "function" && target instanceof Node) {
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
 */
export function openAppContextMenuUnlessTextSelection(
    event: Event,
    openFn: (event: Event) => void,
    options: OpenAppContextMenuOptions = {}
): boolean {
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
