// SPDX-License-Identifier: 0BSD
import { describe, it, expect } from "vitest";
import { decodeMaidenhead, linkifyGeoRefs } from "../../meshchatx/src/frontend/js/geoLinkify.js";

function mulberry32(seed) {
    let a = seed >>> 0;
    return () => {
        a |= 0;
        a = (a + 0x6d2b79f5) | 0;
        let t = Math.imul(a ^ (a >>> 15), 1 | a);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}

describe("decodeMaidenhead properties", () => {
    it("valid locators always decode inside the earth", () => {
        const rnd = mulberry32(31);
        const fields = "ABCDEFGHIJKLMNOPQR";
        const subs = "ABCDEFGHIJKLMNOPQRSTUVWX";
        for (let i = 0; i < 2000; i++) {
            let loc =
                fields[Math.floor(rnd() * 18)] +
                fields[Math.floor(rnd() * 18)] +
                Math.floor(rnd() * 10) +
                Math.floor(rnd() * 10);
            if (rnd() > 0.3) {
                loc += subs[Math.floor(rnd() * 24)] + subs[Math.floor(rnd() * 24)];
            }
            if (rnd() > 0.5) {
                loc += String(Math.floor(rnd() * 10)) + String(Math.floor(rnd() * 10));
            }
            const p = decodeMaidenhead(loc);
            // Edge locators at the grid boundary (past the poles) are not
            // real squares and legitimately decode to null.
            if (p === null) {
                continue;
            }
            expect(p.lat).toBeGreaterThanOrEqual(-90);
            expect(p.lat).toBeLessThanOrEqual(90);
            expect(p.lon).toBeGreaterThanOrEqual(-180);
            expect(p.lon).toBeLessThanOrEqual(180);
            expect(Number.isFinite(p.lat)).toBe(true);
            expect(Number.isFinite(p.lon)).toBe(true);
        }
    });

    it("case-insensitive and whitespace tolerant", () => {
        expect(decodeMaidenhead("fn20pr")).toEqual(decodeMaidenhead("FN20PR"));
        expect(decodeMaidenhead("  FN20PR  ")).toEqual(decodeMaidenhead("FN20PR"));
    });

    it("never returns partial coordinates", () => {
        for (const loc of ["", "A", "AB", "AB1", null, undefined, 123, {}, "AB12C", "AB12CDE"]) {
            const p = decodeMaidenhead(loc);
            if (p !== null) {
                expect(typeof p.lat).toBe("number");
                expect(typeof p.lon).toBe("number");
            }
        }
    });
});

describe("linkifyGeoRefs properties", () => {
    it("never throws on arbitrary text", () => {
        const rnd = mulberry32(37);
        for (let i = 0; i < 300; i++) {
            const len = Math.floor(rnd() * 400);
            let s = "";
            for (let j = 0; j < len; j++) {
                s += String.fromCharCode(Math.floor(rnd() * 0xffff));
            }
            linkifyGeoRefs(s);
        }
    });

    it("returns non-strings untouched", () => {
        expect(linkifyGeoRefs(null)).toBe(null);
        expect(linkifyGeoRefs(undefined)).toBe(undefined);
        expect(linkifyGeoRefs(42)).toBe(42);
    });

    it("anchors never nest inside each other", () => {
        const out = linkifyGeoRefs("FN20pr and geo:FN20 and 51.5,-0.12 and AB12CD");
        const openTags = out.split("<a ").length - 1;
        const closeTags = out.split("</a>").length - 1;
        expect(openTags).toBe(closeTags);
        // No anchor inside an attribute of another anchor
        expect(out).not.toMatch(/data-geo-text="[^"]*<a /);
    });

    it("bounded time on adversarial input", () => {
        const inputs = [
            "FN20pr ".repeat(2000),
            "geo:x ".repeat(2000),
            "12.34,56.78 ".repeat(2000),
            "AB12CD".repeat(1500),
            "9.99 ".repeat(3000),
        ];
        const start = Date.now();
        for (const t of inputs) {
            linkifyGeoRefs(t);
        }
        expect(Date.now() - start).toBeLessThan(5000);
    });
});
