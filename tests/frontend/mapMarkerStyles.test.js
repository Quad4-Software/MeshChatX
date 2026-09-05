// SPDX-License-Identifier: 0BSD

import { describe, it, expect } from "vitest";
import {
    BADGE_SCALE_HOVER,
    BADGE_SCALE_NORMAL,
    DEFAULT_MAP_PIN_PATH,
    DEFAULT_PEER_FACE,
    MARKER_LABEL_MIN_ZOOM,
    buildPeerBadgeSvg,
    clusterBadgeStyle,
    clusterBand,
    contrastGlyphColor,
    contrastRatio,
    encodeSvgDataUrl,
    getCachedClusterStyle,
    getCachedPeerBadgeStyle,
    peerBadgeStyle,
    relativeLuminance,
    shouldShowMarkerLabel,
} from "@/features/map/lib/markerStyles.js";

describe("relativeLuminance / contrastGlyphColor", () => {
    it("rates white brighter than black", () => {
        expect(relativeLuminance("#ffffff")).toBeGreaterThan(relativeLuminance("#000000"));
    });

    it("keeps a preferred glyph when contrast is strong", () => {
        expect(contrastGlyphColor("#3730a3", "#ffffff")).toBe("#ffffff");
        expect(contrastRatio("#ffffff", "#3730a3")).toBeGreaterThanOrEqual(3);
    });

    it("forces a readable glyph when preferred contrast is weak", () => {
        // Light yellow on light yellow face would fail contrast.
        const glyph = contrastGlyphColor("#fef9c3", "#fef08a");
        expect(contrastRatio(glyph, "#fef9c3")).toBeGreaterThanOrEqual(3);
        expect(glyph).toBe("#0f172a");
    });

    it("picks white on dark faces without a preferred color", () => {
        expect(contrastGlyphColor("#0f172a")).toBe("#ffffff");
    });
});

describe("buildPeerBadgeSvg", () => {
    it("includes dual halo rims and a shadow", () => {
        const svg = buildPeerBadgeSvg({
            face: DEFAULT_PEER_FACE,
            glyph: "#ffffff",
            pathD: DEFAULT_MAP_PIN_PATH,
        });
        expect(svg).toContain('class="badge-rim-dark"');
        expect(svg).toContain('class="badge-rim-light"');
        expect(svg).toContain('class="badge-shadow"');
        expect(svg).toContain(DEFAULT_MAP_PIN_PATH);
        expect(svg).not.toContain("<animate");
    });

    it("mutes stale badges and skips pulse", () => {
        const svg = buildPeerBadgeSvg({
            face: "#ff0000",
            glyph: "#00ff00",
            stale: true,
            tracking: true,
        });
        expect(svg).toContain('opacity="0.72"');
        expect(svg).toContain("#64748b");
        expect(svg).toContain("#e2e8f0");
        expect(svg).not.toContain("<animate");
    });

    it("adds pulse animation only when tracking and not stale", () => {
        const svg = buildPeerBadgeSvg({
            face: DEFAULT_PEER_FACE,
            glyph: "#ffffff",
            tracking: true,
            stale: false,
        });
        expect(svg).toContain("<animate");
        expect(svg).toContain('stroke="#38bdf8"');
    });
});

describe("encodeSvgDataUrl", () => {
    it("round-trips a tiny SVG through base64", () => {
        const svg = '<svg xmlns="http://www.w3.org/2000/svg"><circle r="1"/></svg>';
        const url = encodeSvgDataUrl(svg);
        expect(url.startsWith("data:image/svg+xml;base64,")).toBe(true);
        const b64 = url.slice("data:image/svg+xml;base64,".length);
        expect(atob(b64)).toBe(svg);
    });
});

describe("clusterBand", () => {
    it("returns size bands with monotonic radius", () => {
        const small = clusterBand(2);
        const mid = clusterBand(10);
        const large = clusterBand(50);
        expect(small.bandId).toBe("s");
        expect(mid.bandId).toBe("m");
        expect(large.bandId).toBe("l");
        expect(small.radius).toBeLessThan(mid.radius);
        expect(mid.radius).toBeLessThan(large.radius);
        expect(small.face).not.toBe(large.face);
    });

    it("treats boundaries correctly", () => {
        expect(clusterBand(9).bandId).toBe("s");
        expect(clusterBand(10).bandId).toBe("m");
        expect(clusterBand(49).bandId).toBe("m");
        expect(clusterBand(50).bandId).toBe("l");
    });
});

describe("clusterBadgeStyle / getCachedClusterStyle", () => {
    it("returns layered styles with count text", () => {
        const styles = clusterBadgeStyle({ count: 12, hovered: false });
        expect(Array.isArray(styles)).toBe(true);
        expect(styles).toHaveLength(2);
        expect(styles[1].getText().getText()).toBe("12");
    });

    it("returns the same cached object for identical inputs", () => {
        const cache = {};
        const a = getCachedClusterStyle(cache, { count: 7, hovered: false });
        const b = getCachedClusterStyle(cache, { count: 7, hovered: false });
        const c = getCachedClusterStyle(cache, { count: 7, hovered: true });
        expect(a).toBe(b);
        expect(a).not.toBe(c);
    });
});

describe("peerBadgeStyle / getCachedPeerBadgeStyle", () => {
    it("builds a center-anchored Icon style", () => {
        const style = peerBadgeStyle({
            face: DEFAULT_PEER_FACE,
            glyph: "#ffffff",
            label: "Alice",
            showLabel: true,
            scale: BADGE_SCALE_NORMAL,
        });
        const image = style.getImage();
        expect(image.getScale()).toBe(BADGE_SCALE_NORMAL);
        expect(image.getSrc().startsWith("data:image/svg+xml;base64,")).toBe(true);
        expect(image.anchorXUnits_).toBe("fraction");
        expect(image.anchorYUnits_).toBe("fraction");
        expect(image.anchor_).toEqual([0.5, 0.5]);
        expect(style.getText().getText()).toBe("Alice");
    });

    it("omits text when showLabel is false", () => {
        const style = peerBadgeStyle({
            face: DEFAULT_PEER_FACE,
            label: "Hidden",
            showLabel: false,
        });
        expect(style.getText()).toBeNull();
    });

    it("caches peer styles by discrete key", () => {
        const cache = {};
        const a = getCachedPeerBadgeStyle(cache, {
            bgColor: DEFAULT_PEER_FACE,
            iconColor: "#ffffff",
            scale: BADGE_SCALE_HOVER,
            showLabel: false,
        });
        const b = getCachedPeerBadgeStyle(cache, {
            bgColor: DEFAULT_PEER_FACE,
            iconColor: "#ffffff",
            scale: BADGE_SCALE_HOVER,
            showLabel: false,
        });
        expect(a).toBe(b);
    });
});

describe("shouldShowMarkerLabel", () => {
    it("shows labels at or above the min zoom", () => {
        expect(shouldShowMarkerLabel({ zoom: MARKER_LABEL_MIN_ZOOM })).toBe(true);
        expect(shouldShowMarkerLabel({ zoom: MARKER_LABEL_MIN_ZOOM + 1 })).toBe(true);
        expect(shouldShowMarkerLabel({ zoom: MARKER_LABEL_MIN_ZOOM - 1 })).toBe(false);
    });

    it("shows labels when hovered or selected even at low zoom", () => {
        expect(shouldShowMarkerLabel({ zoom: 3, hovered: true })).toBe(true);
        expect(shouldShowMarkerLabel({ zoom: 3, selected: true })).toBe(true);
        expect(shouldShowMarkerLabel({ zoom: 3 })).toBe(false);
    });
});
