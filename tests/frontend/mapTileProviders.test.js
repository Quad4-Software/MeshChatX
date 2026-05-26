import { describe, expect, it } from "vitest";
import {
    detectRasterTileProviderId,
    nextRasterTileProviderId,
    RASTER_TILE_PROVIDER_ORDER,
} from "../../meshchatx/src/frontend/js/mapTileProviders.js";

describe("mapTileProviders", () => {
    it("detects provider from URL", () => {
        expect(detectRasterTileProviderId("https://tiles.openfreemap.org/styles/bright")).toBe("openfreemap");
        expect(detectRasterTileProviderId("https://tile.openstreetmap.org/1/1/1.png")).toBe("osm");
    });

    it("returns next provider not yet attempted", () => {
        expect(nextRasterTileProviderId("openfreemap", [])).toBe("carto-voyager");
        expect(nextRasterTileProviderId("openfreemap", ["carto-voyager"])).toBe("osm");
        expect(nextRasterTileProviderId("carto-light", RASTER_TILE_PROVIDER_ORDER)).toBe(null);
    });
});
