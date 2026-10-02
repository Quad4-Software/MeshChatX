import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
    applyFontFamily,
    applyFontConfig,
    injectCustomFontFace,
    BUNDLED_FONTS,
} from "../../meshchatx/src/frontend/js/fontLoader.js";

describe("fontLoader", () => {
    beforeEach(() => {
        document.getElementById("meshchat-font-loader")?.remove();
        document.getElementById("meshchat-custom-font-face")?.remove();
        vi.restoreAllMocks();
    });

    afterEach(() => {
        document.getElementById("meshchat-font-loader")?.remove();
        document.getElementById("meshchat-custom-font-face")?.remove();
    });

    it("applies bundled font families to body", () => {
        applyFontFamily("inter");
        const el = document.getElementById("meshchat-font-loader");
        expect(el?.textContent).toContain('"Inter"');
    });

    it("system font injects no override", () => {
        applyFontFamily("system");
        expect(document.getElementById("meshchat-font-loader")).toBeNull();
    });

    it("unknown keys inject no override", () => {
        applyFontFamily("does-not-exist");
        expect(document.getElementById("meshchat-font-loader")).toBeNull();
    });

    it("injects @font-face for custom fonts", () => {
        injectCustomFontFace("QUJD", "My Font");
        const el = document.getElementById("meshchat-custom-font-face");
        expect(el?.textContent).toContain('font-family: "My Font"');
        expect(el?.textContent).toContain("data:font/woff2;base64,QUJD");
    });

    it("sanitizes quotes and backslashes in font names", () => {
        injectCustomFontFace("QUJD", 'evil"\\name{}');
        const el = document.getElementById("meshchat-custom-font-face");
        expect(el?.textContent).not.toContain('"\\');
        expect(el?.textContent).toContain('font-family: "evilname{}"');
    });

    it("every BUNDLED_FONTS key has a usable stack", () => {
        for (const [key, stack] of Object.entries(BUNDLED_FONTS)) {
            expect(stack).toMatch(/"/);
            expect(stack.length).toBeGreaterThan(5);
        }
    });
});
