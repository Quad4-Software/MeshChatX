import { describe, expect, it } from "vitest";
import {
    KNOWN_DEFAULT_BASEMAP_URLS,
    PLANET_PM_TILES_URL,
} from "../../meshchatx/src/frontend/js/mapTileProviders.js";
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

describe("planet PMTiles preset", () => {
    it("exposes the Quad4 planet archive as an explicit preset", () => {
        expect(TILE_PROVIDER_URLS["planet-pmtiles"]).toBe(PLANET_PM_TILES_URL);
        expect(PLANET_PM_TILES_URL).toBe("https://s3.quad4.io/pmtiles/planet.pmtiles");
        expect(KNOWN_DEFAULT_BASEMAP_URLS.has(PLANET_PM_TILES_URL)).toBe(true);
        expect(KNOWN_DEFAULT_BASEMAP_URLS.has(DEFAULT_TILE_SERVER_URL)).toBe(true);
        expect(KNOWN_DEFAULT_BASEMAP_URLS.has("https://tiles.example.com/x.png")).toBe(false);
    });

    it("is a vector preset, not part of the raster failover order", () => {
        expect(RASTER_TILE_PROVIDER_ORDER).not.toContain("planet-pmtiles");
        expect(detectRasterTileProviderId(PLANET_PM_TILES_URL)).toBe(null);
    });
});
