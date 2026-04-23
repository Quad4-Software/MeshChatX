import { readFileSync } from "fs";
import { join } from "path";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { clampFloatingToViewport } from "../../meshchatx/src/frontend/js/clampFloatingToViewport.js";

function readSource(relativePath) {
    return readFileSync(join(process.cwd(), relativePath), "utf8");
}

describe("clampFloatingToViewport", () => {
    let innerWidth;
    let innerHeight;

    beforeEach(() => {
        innerWidth = 800;
        innerHeight = 600;
        Object.defineProperty(window, "innerWidth", {
            configurable: true,
            get: () => innerWidth,
        });
        Object.defineProperty(window, "innerHeight", {
            configurable: true,
            get: () => innerHeight,
        });
    });

    it("returns preferred position when panel fits inside the viewport", () => {
        const { left, top, maxHeight } = clampFloatingToViewport(100, 120, 200, 150);
        expect(left).toBe(100);
        expect(top).toBe(120);
        expect(maxHeight).toBeNull();
    });

    it("shifts left when the panel would extend past the right edge", () => {
        const w = 200;
        const { left, top, maxHeight } = clampFloatingToViewport(700, 50, w, 100);
        expect(left).toBe(800 - w - 8);
        expect(top).toBe(50);
        expect(maxHeight).toBeNull();
    });

    it("shifts up when the panel would extend past the bottom edge", () => {
        const h = 200;
        const { left, top, maxHeight } = clampFloatingToViewport(40, 520, 160, h);
        expect(left).toBe(40);
        expect(top).toBe(600 - h - 8);
        expect(maxHeight).toBeNull();
    });

    it("uses custom margin", () => {
        const w = 100;
        const { left } = clampFloatingToViewport(790, 10, w, 50, { margin: 16 });
        expect(left).toBe(800 - w - 16);
    });

    it("returns maxHeight when content is taller than the viewport allows", () => {
        innerHeight = 400;
        Object.defineProperty(window, "innerHeight", {
            configurable: true,
            get: () => innerHeight,
        });
        const { left, top, maxHeight } = clampFloatingToViewport(10, 10, 200, 900);
        expect(left).toBe(10);
        expect(top).toBe(8);
        expect(maxHeight).toBe(400 - 16);
    });

    it("pins wide panels to the left margin when wider than usable width", () => {
        innerWidth = 300;
        Object.defineProperty(window, "innerWidth", {
            configurable: true,
            get: () => innerWidth,
        });
        const { left } = clampFloatingToViewport(50, 10, 500, 40);
        expect(left).toBe(8);
    });
});

describe("clampFloatingToViewport wiring", () => {
    it.each([
        ["DropDownMenu.vue", "meshchatx/src/frontend/components/DropDownMenu.vue", 'ref="dropdownPanel"'],
        ["LanguageSelector.vue", "meshchatx/src/frontend/components/LanguageSelector.vue", 'ref="languageDropdown"'],
        ["NotificationBell.vue", "meshchatx/src/frontend/components/NotificationBell.vue", 'ref="notificationDropdown"'],
        ["ConversationViewer.vue", "meshchatx/src/frontend/components/messages/ConversationViewer.vue", "onReactionPickerDragStart"],
    ])("%s imports the helper and clamps floating UI", (_, relativePath, anchor) => {
        const src = readSource(relativePath);
        expect(src).toContain("clampFloatingToViewport");
        expect(src).toContain(anchor);
    });
});
