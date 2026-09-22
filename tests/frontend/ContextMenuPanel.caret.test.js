import { describe, it, expect } from "vitest";
import ContextMenuPanel from "@/components/contextmenu/ContextMenuPanel.vue";

function callUpdateCaret(x, y, left, top, width, height) {
    const ctx = {
        x,
        y,
        caretStyle: null,
        caretBorderClass: "",
    };
    ContextMenuPanel.methods.updateCaret.call(ctx, left, top, width, height);
    return ctx;
}

describe("ContextMenuPanel caret", () => {
    it("points up toward an origin above the panel", () => {
        const ctx = callUpdateCaret(150, 100, 100, 110, 200, 100);
        expect(ctx.caretStyle).toEqual({ left: "145px", top: "105px" });
        expect(ctx.caretBorderClass).toBe("border-t border-l");
    });

    it("points down toward an origin below the panel", () => {
        const ctx = callUpdateCaret(150, 500, 100, 110, 200, 100);
        expect(ctx.caretStyle).toEqual({ left: "145px", top: "205px" });
        expect(ctx.caretBorderClass).toBe("border-b border-r");
    });

    it("points left toward an origin left of the panel", () => {
        const ctx = callUpdateCaret(50, 150, 100, 110, 200, 100);
        expect(ctx.caretStyle).toEqual({ left: "95px", top: "145px" });
        expect(ctx.caretBorderClass).toBe("border-b border-l");
    });

    it("points right toward an origin right of the panel", () => {
        const ctx = callUpdateCaret(500, 150, 100, 110, 200, 100);
        expect(ctx.caretStyle).toEqual({ left: "295px", top: "145px" });
        expect(ctx.caretBorderClass).toBe("border-t border-r");
    });

    it("hides the caret when the origin is inside the panel", () => {
        const ctx = callUpdateCaret(150, 150, 100, 110, 200, 100);
        expect(ctx.caretStyle).toBeNull();
    });

    it("clamps the caret inside the panel edge near corners", () => {
        // Origin far above and to the right: caret stays within the top edge.
        const ctx = callUpdateCaret(1000, 50, 100, 110, 200, 100);
        expect(ctx.caretStyle.top).toBe("105px");
        // clamped to left + width - margin (100 + 200 - 18 = 282, minus half size 5)
        expect(ctx.caretStyle.left).toBe("277px");
        expect(ctx.caretBorderClass).toBe("border-t border-l");
    });

    it("keeps the caret off the rounded corner on a clamped left edge", () => {
        // Origin above and far left: caret clamps to left + margin (100 + 18
        // = 118, minus half size 5 = 113), clearing the 12px corner curve.
        const ctx = callUpdateCaret(0, 50, 100, 110, 200, 100);
        expect(ctx.caretStyle).toEqual({ left: "113px", top: "105px" });
        expect(ctx.caretBorderClass).toBe("border-t border-l");
    });

    it("hides the caret when the origin sits on the panel edge", () => {
        // Right-click menus anchor at the cursor, which lands on the panel
        // corner or edge. A caret there points at the panel itself.
        const ctx = callUpdateCaret(100, 110, 100, 110, 200, 100);
        expect(ctx.caretStyle).toBeNull();
    });
});
