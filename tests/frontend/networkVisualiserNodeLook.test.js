// SPDX-License-Identifier: 0BSD

/**
 * Regression tests for WebGL visualiser node look:
 * crisp discs, glyph-on-color badges, readable sizes, no soft fuzzy blobs.
 */

import { describe, expect, it } from "vitest";
import {
    ATLAS_CELL,
    isGlyphStyleVisualiserIcon,
    NODE_BORDER_INNER,
    NODE_BORDER_OUTER,
    NODE_EDGE_INNER,
    prepareVisualiserIconPixels,
    resolveVisualiserAssetUrl,
} from "@/js/networkVisualiserWebGL.js";
import {
    graphToSceneRequest,
    KIND_IFACE_ON,
    KIND_ME,
    KIND_PEER,
    webglNodeSizeFor,
} from "@/js/networkVisualiserWebGLEngine.js";

describe("visualiser WebGL node look regressions", () => {
    it("keeps disc soft-edge tight (no fuzzy blob AA)", () => {
        expect(NODE_EDGE_INNER).toBeGreaterThanOrEqual(0.94);
        expect(NODE_BORDER_INNER).toBeLessThan(NODE_BORDER_OUTER);
        expect(NODE_BORDER_OUTER).toBeLessThanOrEqual(NODE_EDGE_INNER + 0.001);
    });

    it("treats network-visualiser badge PNGs as glyph-style icons", () => {
        expect(isGlyphStyleVisualiserIcon("/assets/images/network-visualiser/user.png")).toBe(true);
        expect(isGlyphStyleVisualiserIcon("/assets/images/network-visualiser/interface_connected.png")).toBe(true);
        expect(isGlyphStyleVisualiserIcon("/assets/images/reticulum_logo_512.png")).toBe(false);
        expect(isGlyphStyleVisualiserIcon("")).toBe(false);
    });

    it("uses a high-res atlas cell so icons stay sharp on HiDPI", () => {
        expect(ATLAS_CELL).toBeGreaterThanOrEqual(128);
    });

    it("extracts white glyph and clears solid fill from badge pixels", () => {
        // 2x2: blue fill, white glyph, blue fill, empty
        const data = new Uint8ClampedArray([59, 130, 246, 255, 255, 255, 255, 255, 59, 130, 246, 255, 0, 0, 0, 0]);
        const { painted, glyphPixels } = prepareVisualiserIconPixels(data, "glyph");
        expect(painted).toBe(3);
        expect(glyphPixels).toBe(1);
        expect(data[0]).toBe(0);
        expect(data[3]).toBe(0);
        expect(data[4]).toBe(255);
        expect(data[7]).toBe(255);
        expect(data[8]).toBe(0);
        expect(data[11]).toBe(0);
    });

    it("preserves soft alpha on mid-luma glyph AA fringes", () => {
        // Grey fringe between white glyph and blue fill (binary threshold would crunch this).
        const data = new Uint8ClampedArray([180, 180, 180, 255]);
        const { glyphPixels } = prepareVisualiserIconPixels(data, "glyph");
        expect(glyphPixels).toBe(1);
        expect(data[0]).toBe(255);
        expect(data[1]).toBe(255);
        expect(data[2]).toBe(255);
        expect(data[3]).toBeGreaterThan(40);
        expect(data[3]).toBeLessThan(220);
    });

    it("opaque mode forces alpha on RGB pixels for logo uploads", () => {
        const data = new Uint8ClampedArray([10, 20, 30, 0, 0, 0, 0, 0]);
        const { painted } = prepareVisualiserIconPixels(data, "opaque");
        expect(painted).toBe(1);
        expect(data[3]).toBe(255);
    });

    it("falls back to opaque when glyph extraction would wipe the icon", () => {
        // All mid-saturation blue: no bright glyph pixels.
        const data = new Uint8ClampedArray(16);
        for (let i = 0; i < 16; i += 4) {
            data[i] = 59;
            data[i + 1] = 130;
            data[i + 2] = 246;
            data[i + 3] = 255;
        }
        const backup = new Uint8ClampedArray(data);
        const first = prepareVisualiserIconPixels(data, "glyph");
        expect(first.glyphPixels).toBe(0);
        expect(first.painted).toBe(4);
        // paintSlot restores the pre-glyph buffer before opaque fallback.
        data.set(backup);
        prepareVisualiserIconPixels(data, "opaque");
        expect(data[3]).toBe(255);
        expect(data[0]).toBe(59);
    });

    it("WebGL node sizes stay large enough for glyphs", () => {
        expect(webglNodeSizeFor({ size: 25 }, KIND_PEER)).toBeGreaterThanOrEqual(18);
        expect(webglNodeSizeFor({ size: 50 }, KIND_ME)).toBeGreaterThanOrEqual(30);
        expect(webglNodeSizeFor({ size: 35 }, KIND_IFACE_ON)).toBeGreaterThanOrEqual(24);
        // Must not shrink to the old fuzzy 0.55 scale (~13px for size 25).
        expect(webglNodeSizeFor({ size: 25 }, KIND_PEER)).toBeGreaterThan(16);
    });

    it("graph scene colors use vivid border for disc fill", () => {
        const req = graphToSceneRequest(
            [
                {
                    id: "peer",
                    group: "announce",
                    size: 25,
                    color: { border: "#3b82f6", background: "#eff6ff" },
                },
                {
                    id: "direct",
                    group: "announce",
                    size: 25,
                    color: { border: "#10b981", background: "#ecfdf5" },
                },
            ],
            [],
            { width: 100, height: 100, zoom: 1 }
        );
        expect(req.nodes[0].r).toBeCloseTo(0x3b / 255, 2);
        expect(req.nodes[0].g).toBeCloseTo(0x82 / 255, 2);
        expect(req.nodes[0].b).toBeCloseTo(0xf6 / 255, 2);
        expect(req.nodes[1].r).toBeCloseTo(0x10 / 255, 2);
        expect(req.nodes[1].g).toBeCloseTo(0xb9 / 255, 2);
        // Pale backgrounds must not become the disc color (that looked washed out).
        expect(req.nodes[0].r).toBeGreaterThan(0.15);
        expect(req.nodes[0].size).toBeGreaterThanOrEqual(18);
    });

    it("resolveVisualiserAssetUrl keeps absolute asset paths resolvable", () => {
        const url = resolveVisualiserAssetUrl("/assets/images/network-visualiser/user.png");
        expect(url).toContain("/assets/images/network-visualiser/user.png");
    });
});
