// SPDX-License-Identifier: 0BSD

import { render, cleanup, fireEvent, waitFor } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import MapPage from "@/features/map/MapPage.svelte";
import TileCache from "@/js/TileCache.js";
import GlobalState from "@/js/GlobalState.js";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import en from "@/locales/en.json";

vi.mock("@/js/TileCache.js", () => ({
    default: {
        getTile: vi.fn(),
        setTile: vi.fn(),
        getMapState: vi.fn().mockResolvedValue(null),
        setMapState: vi.fn().mockResolvedValue(),
        clear: vi.fn(),
        initPromise: Promise.resolve(),
    },
}));

function createViewMock() {
    return {
        on: vi.fn(),
        un: vi.fn(),
        setCenter: vi.fn(),
        setZoom: vi.fn(),
        getCenter: vi.fn().mockReturnValue([0, 0]),
        getZoom: vi.fn().mockReturnValue(2),
        getRotation: vi.fn().mockReturnValue(0),
        fit: vi.fn(),
        animate: vi.fn(),
    };
}

function createMapMock(options) {
    const view = options?.view || createViewMock();
    return {
        on: vi.fn(),
        un: vi.fn(),
        addLayer: vi.fn(),
        addControl: vi.fn(),
        removeLayer: vi.fn(),
        addInteraction: vi.fn(),
        removeInteraction: vi.fn(),
        addOverlay: vi.fn(),
        removeOverlay: vi.fn(),
        getView: vi.fn().mockReturnValue(view),
        getLayers: vi.fn().mockReturnValue({
            clear: vi.fn(),
            push: vi.fn(),
            getArray: vi.fn().mockReturnValue([]),
        }),
        getOverlays: vi.fn().mockReturnValue({
            getArray: vi.fn().mockReturnValue([]),
        }),
        forEachFeatureAtPixel: vi.fn(),
        getEventPixel: vi.fn().mockReturnValue([0, 0]),
        getCoordinateFromPixel: vi.fn().mockReturnValue([0, 0]),
        getTargetElement: vi.fn().mockReturnValue({ style: {} }),
        setTarget: vi.fn(),
        updateSize: vi.fn(),
        getViewport: vi.fn().mockReturnValue({
            addEventListener: vi.fn(),
            removeEventListener: vi.fn(),
        }),
    };
}

vi.mock("ol/Map", () => ({ default: vi.fn().mockImplementation(createMapMock) }));
vi.mock("ol/Map.js", () => ({ default: vi.fn().mockImplementation(createMapMock) }));

vi.mock("ol/control/ScaleLine.js", () => ({
    default: vi.fn().mockImplementation(function () {
        return {};
    }),
}));

vi.mock("ol/View", () => ({ default: vi.fn().mockImplementation(createViewMock) }));
vi.mock("ol/View.js", () => ({ default: vi.fn().mockImplementation(createViewMock) }));
vi.mock("ol/layer/Tile", () => ({ default: vi.fn(function () {}) }));
vi.mock("ol/layer/Tile.js", () => ({ default: vi.fn(function () {}) }));
vi.mock("ol/layer/Vector", () => ({ default: vi.fn(function () {}) }));
vi.mock("ol/layer/Vector.js", () => ({ default: vi.fn(function () {}) }));

vi.mock("ol/source/XYZ", () => ({
    default: vi.fn().mockImplementation(function () {
        return {
            getTileLoadFunction: vi.fn().mockReturnValue(vi.fn()),
            setTileLoadFunction: vi.fn(),
        };
    }),
}));
vi.mock("ol/source/XYZ.js", () => ({
    default: vi.fn().mockImplementation(function () {
        return {
            getTileLoadFunction: vi.fn().mockReturnValue(vi.fn()),
            setTileLoadFunction: vi.fn(),
        };
    }),
}));

function createVectorSourceMock() {
    return {
        clear: vi.fn(),
        addFeature: vi.fn(),
        addFeatures: vi.fn(),
        getFeatures: vi.fn().mockReturnValue([]),
        removeFeature: vi.fn(),
        on: vi.fn(),
    };
}

vi.mock("ol/source/Vector", () => ({ default: vi.fn().mockImplementation(createVectorSourceMock) }));
vi.mock("ol/source/Vector.js", () => ({ default: vi.fn().mockImplementation(createVectorSourceMock) }));

vi.mock("ol/proj", () => ({
    fromLonLat: vi.fn((coords) => coords),
    toLonLat: vi.fn((coords) => coords),
}));
vi.mock("ol/proj.js", () => ({
    fromLonLat: vi.fn((coords) => coords),
    toLonLat: vi.fn((coords) => coords),
}));

vi.mock("ol/interaction", () => ({
    Draw: vi.fn().mockImplementation(function () {
        return { on: vi.fn() };
    }),
    Modify: vi.fn().mockImplementation(function () {
        return { on: vi.fn() };
    }),
    Snap: vi.fn().mockImplementation(function () {
        return { on: vi.fn() };
    }),
}));

vi.mock("ol/format/GeoJSON", () => ({
    default: vi.fn().mockImplementation(function () {
        return {
            writeFeaturesObject: vi.fn().mockReturnValue({}),
            readFeatures: vi.fn().mockReturnValue([]),
        };
    }),
}));

describe("MapPage.svelte", () => {
    let axiosMock;

    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages(en);
        axiosMock = {
            get: vi.fn().mockImplementation((url) => {
                if (url.includes("/api/v1/config"))
                    return Promise.resolve({ data: { config: { map_offline_enabled: false } } });
                if (url.includes("/api/v1/map/mbtiles")) return Promise.resolve({ data: [] });
                if (url.includes("/api/v1/lxmf/conversations")) return Promise.resolve({ data: { conversations: [] } });
                if (url.includes("/api/v1/telemetry/peers")) return Promise.resolve({ data: { telemetry: [] } });
                if (url.includes("/api/v1/telemetry/markers")) return Promise.resolve({ data: { markers: [] } });
                if (url.includes("/api/v1/map/offline")) return Promise.resolve({ data: {} });
                if (url.includes("/api/v1/map/data/heard")) return Promise.resolve({ data: { announces: [] } });
                if (url.includes("/api/v1/map/data/status"))
                    return Promise.resolve({ data: { running: false, published_count: 0 } });
                if (url.includes("/api/v1/map/data/published")) return Promise.resolve({ data: { maps: [] } });
                if (url.includes("nominatim")) return Promise.resolve({ data: [] });
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
            patch: vi.fn().mockResolvedValue({ data: {} }),
            delete: vi.fn().mockResolvedValue({ data: {} }),
        };
        vi.stubGlobal("api", axiosMock);
        window.api = axiosMock;
    });

    afterEach(() => {
        cleanup();
        delete window.api;
    });

    it("renders MapPage successfully", async () => {
        const { container } = render(MapPage, {
            embedded: false,
            tabStorageId: "default",
            tabTitle: "Map",
            isActiveTab: true,
        });
        expect(container).toBeTruthy();
    });
});
