import { describe, it, expect, vi, beforeEach } from "vitest";

const getHeaderMock = vi.fn();
const getZxyMock = vi.fn();

vi.mock("pmtiles", () => ({
    PMTiles: vi.fn(function () {
        return {
            getHeader: getHeaderMock,
            getZxy: getZxyMock,
            getMetadata: vi.fn().mockResolvedValue({}),
        };
    }),
    SharedPromiseCache: vi.fn(function () {
        return {};
    }),
}));

const applyStyleMock = vi.fn().mockResolvedValue(undefined);
vi.mock("ol-mapbox-style", () => ({
    applyStyle: (...args) => applyStyleMock(...args),
}));

const basemapLayersMock = vi.fn().mockReturnValue([{ id: "background" }]);
vi.mock("@protomaps/basemaps", () => ({
    layers: (...args) => basemapLayersMock(...args),
    namedFlavor: vi.fn().mockReturnValue({}),
}));

const MODULE_PATH = "../../meshchatx/src/frontend/js/mapPmtilesBasemap.js";

let PLANET_PM_TILES_URL;
let buildPlanetPmtilesBaseMapLayer;

describe("mapPmtilesBasemap", () => {
    beforeEach(async () => {
        vi.clearAllMocks();
        vi.resetModules();
        getHeaderMock.mockResolvedValue({ tileType: 1 });
        getZxyMock.mockResolvedValue({ data: new Uint8Array([1, 2, 3]) });
        const mod = await import(MODULE_PATH);
        PLANET_PM_TILES_URL = mod.PLANET_PM_TILES_URL;
        buildPlanetPmtilesBaseMapLayer = mod.buildPlanetPmtilesBaseMapLayer;
    });

    it("exposes the planet archive URL", () => {
        expect(PLANET_PM_TILES_URL).toBe("https://s3.quad4.io/pmtiles/planet.pmtiles");
    });

    it("validates the archive header before building the layer", async () => {
        await buildPlanetPmtilesBaseMapLayer();
        expect(getHeaderMock).toHaveBeenCalledTimes(1);
    });

    it("rejects when the archive is not a vector tile archive", async () => {
        getHeaderMock.mockResolvedValue({ tileType: 2 });
        await expect(buildPlanetPmtilesBaseMapLayer()).rejects.toThrow(/vector/);
    });

    it("retries archive validation after a failure", async () => {
        getHeaderMock.mockRejectedValueOnce(new Error("offline"));
        await expect(buildPlanetPmtilesBaseMapLayer()).rejects.toThrow("offline");
        getHeaderMock.mockResolvedValue({ tileType: 1 });
        await expect(buildPlanetPmtilesBaseMapLayer()).resolves.toBeTruthy();
        expect(getHeaderMock).toHaveBeenCalledTimes(2);
    });

    it("applies the protomaps style onto the custom vector source", async () => {
        const group = await buildPlanetPmtilesBaseMapLayer();
        expect(group.getLayers().getLength()).toBe(1);
        expect(applyStyleMock).toHaveBeenCalledTimes(1);
        const [layer, styleJson, options] = applyStyleMock.mock.calls[0];
        expect(layer.get("mapbox-source")).toBe("protomaps");
        expect(styleJson.sources.protomaps.url).toBe(`pmtiles://${PLANET_PM_TILES_URL}`);
        expect(styleJson.layers).toEqual([{ id: "background" }]);
        expect(options).toMatchObject({
            source: "protomaps",
            styleUrl: PLANET_PM_TILES_URL,
            updateSource: false,
        });
    });

    async function makeTile(group, tileCoord) {
        const layer = group.getLayers().item(0);
        const source = layer.getSource();
        const tile = {
            tileCoord,
            setLoader: vi.fn((loader) => {
                tile._loader = loader;
            }),
            setFeatures: vi.fn(),
        };
        source.getTileLoadFunction()(tile, "ignored");
        return tile;
    }

    it("loads tiles through archive.getZxy inside the tile loader", async () => {
        const group = await buildPlanetPmtilesBaseMapLayer();
        const tile = await makeTile(group, [3, 4, 3]);
        expect(tile.setLoader).toHaveBeenCalledTimes(1);

        const readFeaturesMock = vi.fn().mockReturnValue(["feature"]);
        const MVT = (await import("ol/format/MVT.js")).default;
        vi.spyOn(MVT.prototype, "readFeatures").mockImplementation(readFeaturesMock);

        await tile._loader([0, 0, 1, 1], 1000, "EPSG:3857");
        await vi.waitFor(() => expect(getZxyMock).toHaveBeenCalledWith(3, 4, 3));
        await vi.waitFor(() => expect(tile.setFeatures).toHaveBeenCalledWith(["feature"]));
        expect(readFeaturesMock).toHaveBeenCalledTimes(1);
    });

    it("marks the tile empty when the archive has no data for it", async () => {
        getZxyMock.mockResolvedValue(null);
        const group = await buildPlanetPmtilesBaseMapLayer();
        const tile = await makeTile(group, [0, 0, 0]);
        await tile._loader([0, 0, 1, 1], 1000, "EPSG:3857");
        await vi.waitFor(() => expect(tile.setFeatures).toHaveBeenCalledWith([]));
    });

    it("marks the tile empty when the tile fetch fails", async () => {
        getZxyMock.mockRejectedValue(new Error("range request failed"));
        const group = await buildPlanetPmtilesBaseMapLayer();
        const tile = await makeTile(group, [1, 1, 1]);
        await tile._loader([0, 0, 1, 1], 1000, "EPSG:3857");
        await vi.waitFor(() => expect(tile.setFeatures).toHaveBeenCalledWith([]));
    });
});
