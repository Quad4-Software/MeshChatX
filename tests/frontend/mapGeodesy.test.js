// SPDX-License-Identifier: 0BSD

import { describe, it, expect } from "vitest";
import { getDistance } from "ol/sphere";
import {
    sphericalInitialBearingDeg,
    rhumbLineMetrics,
    computeSegmentMetrics,
    formatLengthPairMeters,
    buildBearingOverlayHtml,
    buildBearingLiveTooltipHtml,
} from "@/js/mapGeodesy.js";

describe("mapGeodesy", () => {
    it("sphericalInitialBearingDeg: due east on equator", () => {
        const b = sphericalInitialBearingDeg(0, 0, 1, 0);
        expect(b).toBeCloseTo(90, 0);
    });

    it("sphericalInitialBearingDeg: due north along meridian", () => {
        const b = sphericalInitialBearingDeg(0, 0, 0, 1);
        expect(b).toBeCloseTo(0, 0);
    });

    it("computeSegmentMetrics: back azimuth equals initial bearing reversed", () => {
        const m = computeSegmentMetrics(-0.1276, 51.5074, 2.3522, 48.8566);
        const rev = computeSegmentMetrics(2.3522, 48.8566, -0.1276, 51.5074);
        expect(m.forwardAzimuthDeg).toBeCloseTo(rev.backAzimuthDeg, 0);
        expect(m.backAzimuthDeg).toBeCloseTo(rev.forwardAzimuthDeg, 0);
    });

    it("computeSegmentMetrics: geodesic distance matches ol/sphere getDistance", () => {
        const lon1 = -0.1276;
        const lat1 = 51.5074;
        const lon2 = 2.3522;
        const lat2 = 48.8566;
        const m = computeSegmentMetrics(lon1, lat1, lon2, lat2);
        const d = getDistance([lon1, lat1], [lon2, lat2]);
        expect(m.geodesicMeters).toBeCloseTo(d, 4);
        expect(m.geodesicMeters).toBeGreaterThan(330_000);
        expect(m.geodesicMeters).toBeLessThan(360_000);
    });

    it("rhumbLineMetrics: east on equator has bearing 90", () => {
        const r = rhumbLineMetrics(0, 0, 10, 0);
        expect(r.bearingDeg).toBeCloseTo(90, 0);
        expect(r.distanceMeters).toBeCloseTo(getDistance([0, 0], [10, 0]), -2);
    });

    it("formatLengthPairMeters formats short and long", () => {
        const s = formatLengthPairMeters(50);
        expect(s.metric).toMatch(/m$/);
        const l = formatLengthPairMeters(5000);
        expect(l.metric).toMatch(/km/);
    });

    it("buildBearingOverlayHtml escapes and includes labels", () => {
        const m = computeSegmentMetrics(0, 0, 0.1, 0);
        const html = buildBearingOverlayHtml(m, (k) =>
            k === "map.bearing_geodesic" ? "Geodesic<script>evil()</script>" : k
        );
        expect(html).not.toContain("<script>");
        expect(html).toContain("Geodesic");
        expect(html).toContain("map.bearing_forward");
    });

    it("buildBearingLiveTooltipHtml produces compact string", () => {
        const m = computeSegmentMetrics(0, 0, 0, 0.5);
        const h = buildBearingLiveTooltipHtml(m, (k) => k);
        expect(h).toContain("map.bearing_geodesic");
        expect(h).toContain("<br/>");
    });
});
