import { describe, it, expect } from "vitest";
import { computeCaret } from "@/js/contextMenuCaret.ts";

describe("ContextMenuPanel caret", () => {
    it("points up toward an origin above the panel", () => {
        const caret = computeCaret(150, 100, 100, 110, 200, 100);
        expect(caret.style).toEqual({ left: "145px", top: "105px" });
        expect(caret.borderClass).toBe("border-t border-l");
    });

    it("points down toward an origin below the panel", () => {
        const caret = computeCaret(150, 500, 100, 110, 200, 100);
        expect(caret.style).toEqual({ left: "145px", top: "205px" });
        expect(caret.borderClass).toBe("border-b border-r");
    });

    it("points left toward an origin left of the panel", () => {
        const caret = computeCaret(50, 150, 100, 110, 200, 100);
        expect(caret.style).toEqual({ left: "95px", top: "145px" });
        expect(caret.borderClass).toBe("border-b border-l");
    });

    it("points right toward an origin right of the panel", () => {
        const caret = computeCaret(500, 150, 100, 110, 200, 100);
        expect(caret.style).toEqual({ left: "295px", top: "145px" });
        expect(caret.borderClass).toBe("border-t border-r");
    });

    it("hides the caret when the origin is inside the panel", () => {
        const caret = computeCaret(150, 150, 100, 110, 200, 100);
        expect(caret).toBeNull();
    });

    it("clamps the caret inside the panel edge near corners", () => {
        // Origin far above and to the right: caret stays within the top edge.
        const caret = computeCaret(1000, 50, 100, 110, 200, 100);
        expect(caret.style.top).toBe("105px");
        // clamped to left + width - margin (100 + 200 - 12 = 288, minus half size 5)
        expect(caret.style.left).toBe("283px");
        expect(caret.borderClass).toBe("border-t border-l");
    });
});
