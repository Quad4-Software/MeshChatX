import { describe, it, expect } from "vitest";
import {
    DEFAULT_RRC_HUB_ICON,
    buildMdiIconNames,
    isValidMdiIconName,
    normalizeMdiIconName,
} from "@/js/mdiIconNames.js";

describe("mdiIconNames", () => {
    it("accepts known mdi icon names", () => {
        const names = buildMdiIconNames();
        expect(names.length).toBeGreaterThan(100);
        expect(isValidMdiIconName("forum-outline")).toBe(true);
        expect(normalizeMdiIconName("Forum-Outline")).toBe("forum-outline");
    });

    it("rejects invalid names", () => {
        expect(isValidMdiIconName("")).toBe(false);
        expect(isValidMdiIconName("bad icon")).toBe(false);
        expect(normalizeMdiIconName(null)).toBe(null);
        expect(normalizeMdiIconName("")).toBe(null);
    });

    it("has a default hub icon", () => {
        expect(DEFAULT_RRC_HUB_ICON).toBe("forum-outline");
        expect(isValidMdiIconName(DEFAULT_RRC_HUB_ICON)).toBe(true);
    });
});
