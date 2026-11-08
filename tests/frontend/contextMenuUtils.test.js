/* SPDX-License-Identifier: 0BSD */

import { describe, it, expect, vi, afterEach } from "vitest";
import {
    preferNativeTextSelectionMenu,
    openAppContextMenuUnlessTextSelection,
    isTouchContextMenu,
    pointHitsSelectableText,
    shouldOpenCustomContextMenu,
} from "../../meshchatx/src/frontend/js/contextMenuUtils.js";

describe("contextMenuUtils", () => {
    afterEach(() => {
        vi.restoreAllMocks();
        window.getSelection()?.removeAllRanges?.();
    });

    it("prefers native menu for input targets", () => {
        const input = document.createElement("input");
        document.body.appendChild(input);
        try {
            expect(preferNativeTextSelectionMenu({ target: input })).toBe(true);
        } finally {
            input.remove();
        }
    });

    it("prefers native menu when a non-empty selection exists", () => {
        const p = document.createElement("p");
        p.textContent = "hello world";
        document.body.appendChild(p);
        try {
            const range = document.createRange();
            range.selectNodeContents(p);
            const selection = window.getSelection();
            selection.removeAllRanges();
            selection.addRange(range);
            expect(preferNativeTextSelectionMenu({ target: p })).toBe(true);
        } finally {
            window.getSelection()?.removeAllRanges?.();
            p.remove();
        }
    });

    it("allows app menu when selection is collapsed", () => {
        const p = document.createElement("p");
        p.textContent = "hello";
        document.body.appendChild(p);
        try {
            window.getSelection()?.removeAllRanges?.();
            expect(preferNativeTextSelectionMenu({ target: p })).toBe(false);
        } finally {
            p.remove();
        }
    });

    it("does not prefer native menu when selection is unrelated to the event target", () => {
        const selected = document.createElement("p");
        selected.textContent = "selected";
        const other = document.createElement("p");
        other.textContent = "other";
        document.body.appendChild(selected);
        document.body.appendChild(other);
        try {
            const range = document.createRange();
            range.selectNodeContents(selected);
            const selection = window.getSelection();
            selection.removeAllRanges();
            selection.addRange(range);
            expect(preferNativeTextSelectionMenu({ target: other })).toBe(false);
        } finally {
            window.getSelection()?.removeAllRanges?.();
            selected.remove();
            other.remove();
        }
    });

    it("openAppContextMenuUnlessTextSelection preventDefaults only for app menus", () => {
        const openFn = vi.fn();
        const event = {
            target: document.body,
            preventDefault: vi.fn(),
            stopPropagation: vi.fn(),
        };
        window.getSelection()?.removeAllRanges?.();
        expect(openAppContextMenuUnlessTextSelection(event, openFn, { stopPropagation: true })).toBe(true);
        expect(event.preventDefault).toHaveBeenCalled();
        expect(event.stopPropagation).toHaveBeenCalled();
        expect(openFn).toHaveBeenCalledWith(event);

        const input = document.createElement("input");
        document.body.appendChild(input);
        try {
            const nativeEvent = {
                target: input,
                preventDefault: vi.fn(),
                stopPropagation: vi.fn(),
            };
            const openNative = vi.fn();
            expect(openAppContextMenuUnlessTextSelection(nativeEvent, openNative)).toBe(false);
            expect(nativeEvent.preventDefault).not.toHaveBeenCalled();
            expect(openNative).not.toHaveBeenCalled();
        } finally {
            input.remove();
        }
    });
    it("isTouchContextMenu detects pointerType touch and mouse", () => {
        expect(isTouchContextMenu({ pointerType: "touch" })).toBe(true);
        expect(isTouchContextMenu({ pointerType: "mouse" })).toBe(false);
        expect(isTouchContextMenu({ sourceCapabilities: { firesTouchEvents: true } })).toBe(true);
        expect(isTouchContextMenu(null)).toBe(false);
    });

    it("isTouchContextMenu falls back to a recent touchstart", () => {
        window.dispatchEvent(new Event("touchstart"));
        expect(isTouchContextMenu({})).toBe(true);
    });

    it("pointHitsSelectableText uses caretRangeFromPoint when available", () => {
        const p = document.createElement("p");
        p.textContent = "selectable";
        document.body.appendChild(p);
        const orig = document.caretRangeFromPoint;
        try {
            document.caretRangeFromPoint = () => ({ startContainer: p.firstChild });
            expect(pointHitsSelectableText({ clientX: 1, clientY: 1 })).toBe(true);
            document.caretRangeFromPoint = () => ({ startContainer: p });
            expect(pointHitsSelectableText({ clientX: 1, clientY: 1 })).toBe(false);
            document.caretRangeFromPoint = orig;
        } finally {
            p.remove();
            if (orig) document.caretRangeFromPoint = orig; else delete document.caretRangeFromPoint;
        }
    });

    it("shouldOpenCustomContextMenu suppresses touch long-press on text", () => {
        const orig = document.caretRangeFromPoint;
        vi.useFakeTimers();
        try {
            document.caretRangeFromPoint = () => ({ startContainer: document.createTextNode("x") });
            expect(shouldOpenCustomContextMenu({ pointerType: "touch", clientX: 1, clientY: 1 })).toBe(false);
            vi.setSystemTime(Date.now() + 2000);
            expect(shouldOpenCustomContextMenu({ pointerType: "mouse", clientX: 1, clientY: 1 })).toBe(true);
        } finally {
            vi.useRealTimers();
            if (orig) document.caretRangeFromPoint = orig; else delete document.caretRangeFromPoint;
        }
    });
});
