// SPDX-License-Identifier: 0BSD
import { describe, it, expect, vi, beforeEach } from "vitest";
import TileLayer from "ol/layer/Tile.js";
import VectorTileLayer from "ol/layer/VectorTile.js";

const headers = {
    vector: {
        tileType: 1,
        minZoom: 0,
        maxZoom: 14,
        minLon: -10,
        minLat: -10,
        maxLon: 10,
        maxLat: 10,
    },
    raster: {
        tileType: 2,
        minZoom: 3,
        maxZoom: 12,
        minLon: -5,
        minLat: 40,
        maxLon: 5,
        maxLat: 50,
    },
};

let currentHeader = headers.vector;
const getZxy = vi.fn(async () => ({ data: new Uint8Array([1, 2, 3]) }));
const applyStyleCalls = [];

let failHeader = false;
vi.mock("pmtiles", () => ({
    PMTiles: class {
        constructor() {}
        async getHeader() {
            if (failHeader) throw new Error("cannot read header");
            return currentHeader;
        }
        getZxy(...args) {
            return getZxy(...args);
        }
    },
    SharedPromiseCache: class {
        constructor() {}
    },
}));

vi.mock("ol-mapbox-style", () => ({
    applyStyle: vi.fn(async (layer, styleJson) => {
        applyStyleCalls.push(styleJson);
    }),
}));

vi.mock("../../meshchatx/src/frontend/js/pmtilesCacheSource.js", () => ({
    getCachedPmtilesSource: vi.fn(() => ({ getBytes: async () => ({ data: new ArrayBuffer(0) }) })),
}));

import { buildLocalPmtilesBaseMapLayer } from "../../meshchatx/src/frontend/js/mapPmtilesBasemap.js";

beforeEach(() => {
    currentHeader = headers.vector;
    failHeader = false;
    applyStyleCalls.length = 0;
    getZxy.mockClear();
});

describe("buildLocalPmtilesBaseMapLayer raster branch", () => {
    it("returns a plain tile layer for raster archives", async () => {
        currentHeader = headers.raster;
        const { layer, header } = await buildLocalPmtilesBaseMapLayer("/api/v1/map/pmtiles/region.pmtiles");
        expect(header.tileType).toBe(2);
        const inner = layer.getLayers().getArray();
        expect(inner.length).toBe(1);
        expect(inner[0]).toBeInstanceOf(TileLayer);
        expect(inner[0]).not.toBeInstanceOf(VectorTileLayer);
        // Raster path applies no Mapbox style.
        expect(applyStyleCalls.length).toBe(0);
    });

    it("clamps the tile grid to the archive zoom range", async () => {
        currentHeader = headers.raster;
        const { layer } = await buildLocalPmtilesBaseMapLayer("/api/v1/map/pmtiles/region.pmtiles");
        const grid = layer.getLayers().getArray()[0].getSource().getTileGrid();
        expect(grid.getMinZoom()).toBe(3);
        expect(grid.getMaxZoom()).toBe(12);
    });

    it("clamps the layer extent to the archive bounds", async () => {
        currentHeader = headers.raster;
        const { layer } = await buildLocalPmtilesBaseMapLayer("/api/v1/map/pmtiles/region.pmtiles");
        const extent = layer.getLayers().getArray()[0].getExtent();
        expect(Array.isArray(extent)).toBe(true);
        // -5..5 lon in EPSG:3857 is roughly +/-556597
        expect(extent[0]).toBeLessThan(-500000);
        expect(extent[2]).toBeGreaterThan(500000);
    });

    it("skips the extent when header bounds are degenerate", async () => {
        currentHeader = { ...headers.raster, minLon: 5, maxLon: 5 };
        const { layer } = await buildLocalPmtilesBaseMapLayer("/api/v1/map/pmtiles/region.pmtiles");
        expect(layer.getLayers().getArray()[0].getExtent()).toBeUndefined();
    });
});

describe("buildLocalPmtilesBaseMapLayer vector branch", () => {
    it("returns a vector tile layer styled without remote sprites", async () => {
        const { layer } = await buildLocalPmtilesBaseMapLayer("/api/v1/map/pmtiles/region.pmtiles");
        const inner = layer.getLayers().getArray();
        expect(inner[0]).toBeInstanceOf(VectorTileLayer);
        expect(applyStyleCalls.length).toBe(1);
        // Offline: the style JSON must not reference the remote sprite.
        expect(applyStyleCalls[0].sprite).toBeUndefined();
        // Trimmed style: the one-way overlay is dropped.
        const ids = applyStyleCalls[0].layers.map((l) => l.id);
        expect(ids).not.toContain("roads_oneway");
        expect(ids).toContain("water");
    });

    it("propagates archive open failures so the caller can fall back", async () => {
        failHeader = true;
        await expect(buildLocalPmtilesBaseMapLayer("/api/v1/map/pmtiles/gone.pmtiles")).rejects.toThrow(
            "cannot read header"
        );
    });
});
