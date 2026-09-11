import { describe, it, expect } from "vitest";
import { decodeMaidenhead, linkifyGeoRefs, resolveGeoText } from "../../meshchatx/src/frontend/js/geoLinkify.js";

describe("geoLinkify", () => {
    it("decodes a 6-char Maidenhead locator to its square center", () => {
        // FN20pr: field FN, square 20, subsquare pr.
        const p = decodeMaidenhead("FN20pr");
        expect(p).not.toBeNull();
        // Field F = lon 100..120 -> -80..-60; N = lat 130..140 -> 40..50
        // square 20 -> lon -76..-74, lat 40..41; subsquare p,r.
        expect(p.lon).toBeGreaterThan(-76);
        expect(p.lon).toBeLessThan(-74);
        expect(p.lat).toBeGreaterThan(40);
        expect(p.lat).toBeLessThan(42);
    });

    it("decodes the 4-char field+square form", () => {
        const p = decodeMaidenhead("FN20");
        expect(p.lat).toBeCloseTo(40.5, 3);
        expect(p.lon).toBeCloseTo(-75, 3);
    });

    it("rejects invalid locators", () => {
        expect(decodeMaidenhead("ZZ99")).toBeNull();
        expect(decodeMaidenhead("F1")).toBeNull();
        expect(decodeMaidenhead("")).toBeNull();
        expect(decodeMaidenhead(null)).toBeNull();
    });

    it("never crashes or returns NaN on odd-length and garbage input", () => {
        for (const s of ["FN20p", "FN20pr4", "AA00", "RR99xx99", "a", "12", "0x", "FN20ZZ"]) {
            const p = decodeMaidenhead(s);
            if (p !== null) {
                expect(Number.isFinite(p.lat)).toBe(true);
                expect(Number.isFinite(p.lon)).toBe(true);
            }
        }
    });

    it("linkifies maidenhead locators in escaped text", () => {
        const out = linkifyGeoRefs("my grid is FN20pr today");
        expect(out).toContain('class="geo-link ');
        expect(out).toContain('data-geo-text="FN20pr"');
    });

    it("does not linkify short 4-char grid tokens inline", () => {
        const out = linkifyGeoRefs("the AB12 part number");
        expect(out).not.toContain("geo-link");
    });

    it("linkifies explicit geo: prefixes", () => {
        const out = linkifyGeoRefs("meet at geo:FN20pr");
        expect(out).toContain('data-geo-text="FN20pr"');
    });

    it("linkifies plausible lat/lon pairs and rejects out-of-range", () => {
        expect(linkifyGeoRefs("48.1372, 11.5755")).toContain("geo-link");
        expect(linkifyGeoRefs("999.5, 200.1")).not.toContain("geo-link");
        expect(linkifyGeoRefs("version 1.2, 3.4 more")).toContain("geo-link"); // known fuzzy case, still valid coords
    });

    it("resolves a maidenhead locator without geo wasm", async () => {
        const p = await resolveGeoText("FN20pr");
        expect(p).not.toBeNull();
        expect(p.kind).toBe("grid");
    });

    it("returns null for unresolvable text", async () => {
        const p = await resolveGeoText("just words");
        expect(p).toBeNull();
    });
});
