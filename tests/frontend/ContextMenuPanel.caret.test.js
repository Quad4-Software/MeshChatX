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
        // clamped to left + width - margin (100 + 200 - 18 = 282, minus half size 5)
        expect(caret.style.left).toBe("277px");
        expect(caret.borderClass).toBe("border-t border-l");
    });

    it("keeps the caret off the rounded corner on a clamped left edge", () => {
        // Origin above and far left: caret clamps to left + margin (100 + 18
        // = 118, minus half size 5 = 113), clearing the 12px corner curve.
        const caret = computeCaret(0, 50, 100, 110, 200, 100);
        expect(caret.style).toEqual({ left: "113px", top: "105px" });
        expect(caret.borderClass).toBe("border-t border-l");
    });

    it("hides the caret when the origin sits on the panel edge", () => {
        // Right-click menus anchor at the cursor, which lands on the panel
        // corner or edge. A caret there points at the panel itself.
        const caret = computeCaret(100, 110, 100, 110, 200, 100);
        expect(caret).toBeNull();
    });
});
