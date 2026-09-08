import { describe, expect, it } from "vitest";
import {
    DEFAULT_TILE_SERVER_URL,
    detectRasterTileProviderId,
    nextRasterTileProviderId,
    RASTER_TILE_PROVIDER_ORDER,
    TILE_PROVIDER_URLS,
} from "../../meshchatx/src/frontend/js/mapTileProviders.js";

describe("mapTileProviders", () => {
    it("defaults to OSM raster URL", () => {
        expect(DEFAULT_TILE_SERVER_URL).toBe("https://tile.openstreetmap.org/{z}/{x}/{y}.png");
        expect(TILE_PROVIDER_URLS.osm).toBe(DEFAULT_TILE_SERVER_URL);
        expect(RASTER_TILE_PROVIDER_ORDER[0]).toBe("osm");
    });

    it("detects provider from URL", () => {
        expect(detectRasterTileProviderId("https://tiles.openfreemap.org/styles/bright")).toBe(null);
        expect(detectRasterTileProviderId("https://tile.openstreetmap.org/1/1/1.png")).toBe("osm");
        expect(detectRasterTileProviderId("https://evil.example/tiles.openfreemap.org/x")).toBe(null);
        expect(detectRasterTileProviderId("https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png")).toBe(
            "carto-dark"
        );
    });

    it("returns next provider not yet attempted", () => {
        expect(nextRasterTileProviderId("osm", [])).toBe("carto-dark");
        expect(nextRasterTileProviderId("carto-dark", [])).toBe("carto-voyager");
        expect(nextRasterTileProviderId("carto-light", [])).toBe("osm");
        expect(nextRasterTileProviderId("osm", ["carto-dark", "carto-voyager", "carto-light"])).toBe(null);
    });
});
