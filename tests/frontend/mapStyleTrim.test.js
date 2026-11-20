import { describe, it, expect } from "vitest";
import { layers as basemapLayers, namedFlavor } from "@protomaps/basemaps";
import {
    trimBasemapLayers,
    partitionBasemapLayers,
    REQUIRED_LAYER_IDS,
} from "../../meshchatx/src/frontend/js/mapStyleTrim.js";

const stock = basemapLayers("protomaps", namedFlavor("light"), { lang: "en" });
const trimmed = trimBasemapLayers(stock);
const { geometry, symbols } = partitionBasemapLayers(trimmed);

function visibleAtZoom(list, z) {
    return list.filter((l) => (l.minzoom ?? 0) <= z && (l.maxzoom ?? 30) > z).length;
}

describe("trimBasemapLayers", () => {
    it("keeps every orientation-critical layer", () => {
        const ids = new Set(trimmed.map((l) => l.id));
        for (const id of REQUIRED_LAYER_IDS) {
            expect(ids.has(id), id).toBe(true);
        }
    });

    it("drops the one-way arrow overlay", () => {
        expect(trimmed.find((l) => l.id === "roads_oneway")).toBeUndefined();
    });

    it("raises minzoom for detail layers without touching stock ranges", () => {
        const at = (id) => trimmed.find((l) => l.id === id);
        expect(at("buildings").minzoom).toBe(13);
        expect(at("roads_minor").minzoom).toBe(13);
        expect(at("pois").minzoom).toBe(14);
        expect(at("roads_highway").minzoom ?? 0).toBe(0);
        expect(at("water").minzoom ?? 0).toBe(0);
    });

    it("cuts the number of layers evaluated at low zoom substantially", () => {
        // Perf guard: at world zoom the trimmed style must evaluate far
        // fewer layers than the stock style, the mechanism behind the
        // reduced per-frame replay cost.
        const stockActive0 = visibleAtZoom(stock, 2);
        const trimmedActive0 = visibleAtZoom(trimmed, 2);
        expect(trimmedActive0).toBeLessThanOrEqual(stockActive0 * 0.7);
        // Mid zoom is where the overrides hide minor roads, tunnels and
        // landuse detail. At z14+ nearly everything is visible anyway.
        for (const z of [5, 10]) {
            expect(visibleAtZoom(trimmed, z)).toBeLessThan(visibleAtZoom(stock, z));
        }
        // Close zoom keeps the detail the user zoomed in to see.
        expect(visibleAtZoom(trimmed, 14)).toBeGreaterThanOrEqual(visibleAtZoom(stock, 14) - 2);
    });

    it("does not mutate the stock layer objects", () => {
        const before = stock.find((l) => l.id === "buildings").minzoom;
        expect(before).toBeUndefined();
    });
});

describe("partitionBasemapLayers", () => {
    it("splits every layer into exactly one of geometry or symbols", () => {
        expect(geometry.length + symbols.length).toBe(trimmed.length);
        expect(symbols.every((l) => l.type === "symbol")).toBe(true);
        expect(geometry.every((l) => l.type !== "symbol")).toBe(true);
    });

    it("keeps place labels in the symbol group", () => {
        const symIds = new Set(symbols.map((l) => l.id));
        expect(symIds.has("places_country")).toBe(true);
        expect(symIds.has("places_locality")).toBe(true);
    });
});
