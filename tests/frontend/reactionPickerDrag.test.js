// SPDX-License-Identifier: 0BSD

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import {
    startReactionPickerDrag,
    styleForReactionPickerDragPos,
} from "../../meshchatx/src/frontend/features/messages/lib/reactionPickerDrag.ts";

describe("reactionPickerDrag", () => {
    beforeEach(() => {
        Object.defineProperty(window, "innerWidth", {
            configurable: true,
            get: () => 800,
        });
        Object.defineProperty(window, "innerHeight", {
            configurable: true,
            get: () => 600,
        });
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("builds fixed-position CSS for a dragged panel", () => {
        expect(styleForReactionPickerDragPos({ x: 12, y: 34 })).toBe("position:fixed;left:12px;top:34px;");
    });

    it("moves and clamps the panel to the viewport", () => {
        const setPosition = vi.fn();
        const panel = {
            getBoundingClientRect: () => ({
                left: 100,
                top: 80,
                width: 200,
                height: 150,
                right: 300,
                bottom: 230,
            }),
        };
        const cleanup = startReactionPickerDrag({
            event: { clientX: 110, clientY: 90 },
            getPanel: () => panel,
            setPosition,
        });
        expect(cleanup).toBeTypeOf("function");

        document.dispatchEvent(
            new MouseEvent("mousemove", {
                clientX: 750,
                clientY: 500,
                bubbles: true,
                cancelable: true,
            })
        );

        expect(setPosition).toHaveBeenCalledWith({
            x: 800 - 200 - 8,
            y: 600 - 150 - 8,
        });

        cleanup();
    });

    it("returns null when the panel is missing", () => {
        expect(
            startReactionPickerDrag({
                event: { clientX: 1, clientY: 2 },
                getPanel: () => null,
                setPosition: vi.fn(),
            })
        ).toBeNull();
    });

    it("removes listeners on cleanup and mouseup", () => {
        const setPosition = vi.fn();
        const panel = {
            getBoundingClientRect: () => ({
                left: 40,
                top: 40,
                width: 100,
                height: 80,
                right: 140,
                bottom: 120,
            }),
        };
        const cleanup = startReactionPickerDrag({
            event: { clientX: 50, clientY: 50 },
            getPanel: () => panel,
            setPosition,
        });

        document.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
        document.dispatchEvent(
            new MouseEvent("mousemove", {
                clientX: 80,
                clientY: 70,
                bubbles: true,
                cancelable: true,
            })
        );
        expect(setPosition).not.toHaveBeenCalled();

        cleanup();
    });
});
