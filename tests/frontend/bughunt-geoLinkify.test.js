// SPDX-License-Identifier: 0BSD
// Bug-hunt: geoLinkify.linkifyGeoRefs O(matches^2) overlap scan.
import { describe, expect, it } from "vitest";
import { linkifyGeoRefs } from "../../meshchatx/src/frontend/js/geoLinkify.js";

function timeMs(fn) {
    const t0 = performance.now();
    fn();
    return performance.now() - t0;
}

describe("bughunt: linkifyGeoRefs overlap scan complexity", () => {
    it("correctness: still linkifies and skips overlaps", () => {
        const out = linkifyGeoRefs("grid FN20pr and 48.8, 2.3 here");
        expect(out).toContain("geo-link");
        expect(out).toContain('data-geo-text="FN20pr"');
    });

    it("does not take >500ms on a 224KB all-maidenhead message", () => {
        // addMatch() linearly scans every already-claimed range for each new
        // candidate: O(m^2). Measured ~1.17s at 32k matches (~224KB text).
        const text = Array.from({ length: 32000 }, () => `FN20pr`).join(" ");
        const t = timeMs(() => linkifyGeoRefs(text));
        expect(t, `linkifyGeoRefs took ${t.toFixed(0)}ms on 32k matches`).toBeLessThan(500);
    });

    it("scales superlinearly across 8k->16k->32k", () => {
        const t = (n) => timeMs(() => linkifyGeoRefs(Array.from({ length: n }, () => `FN20pr`).join(" ")));
        const a = t(8000);
        const b = t(16000);
        const c = t(32000);
        // O(m) => ~2x per doubling; O(m^2) => ~4x. Require clearly sub-quadratic.
        expect(c / Math.max(b, 0.5), `8k=${a.toFixed(0)} 16k=${b.toFixed(0)} 32k=${c.toFixed(0)}ms`).toBeLessThan(3.4);
    });
});
