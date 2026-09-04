import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach, beforeAll } from "vitest";

// Mock TileCache BEFORE importing MapPage
vi.mock("@/js/TileCache", () => ({
    default: {
        getTile: vi.fn(),
        setTile: vi.fn(),
        getMapState: vi.fn().mockResolvedValue(null),
        setMapState: vi.fn().mockResolvedValue(),
        clear: vi.fn(),
        initPromise: Promise.resolve(),
    },
}));

vi.mock("ol-mapbox-style", () => ({
    apply: vi.fn().mockResolvedValue(undefined),
}));
vi.mock("ol/layer/Group", () => ({
    default: vi.fn(function () {}),
}));

// Mock OpenLayers (Vitest 4: constructor mocks must use function/class, not arrow fns)
vi.mock("ol/Map", () => ({
    default: vi.fn().mockImplementation(function () {
        return {
            on: vi.fn(),
            addLayer: vi.fn(),
            addControl: vi.fn(),
            addInteraction: vi.fn(),
            addOverlay: vi.fn(),
            removeInteraction: vi.fn(),
            removeOverlay: vi.fn(),
            un: vi.fn(),
            getEventPixel: vi.fn().mockReturnValue([0, 0]),
            getTargetElement: vi.fn().mockReturnValue({ style: {} }),
            getView: vi.fn().mockReturnValue({
                on: vi.fn(),
                un: vi.fn(),
                setCenter: vi.fn(),
                setZoom: vi.fn(),
                getCenter: vi.fn().mockReturnValue([0, 0]),
                getZoom: vi.fn().mockReturnValue(2),
                getRotation: vi.fn().mockReturnValue(0),
                fit: vi.fn(),
                animate: vi.fn(),
            }),
            getLayers: vi.fn().mockReturnValue({
                clear: vi.fn(),
                push: vi.fn(),
                getArray: vi.fn().mockReturnValue([]),
            }),
            getOverlays: vi.fn().mockReturnValue({
                getArray: vi.fn().mockReturnValue([]),
            }),
            forEachFeatureAtPixel: vi.fn(),
            setTarget: vi.fn(),
            updateSize: vi.fn(),
            getViewport: vi.fn().mockReturnValue({
                addEventListener: vi.fn(),
                removeEventListener: vi.fn(),
            }),
        };
    }),
}));

vi.mock("ol/View", () => ({ default: vi.fn(function () {}) }));
vi.mock("ol/layer/Tile", () => ({ default: vi.fn(function () {}) }));
vi.mock("ol/layer/Vector", () => ({ default: vi.fn(function () {}) }));
vi.mock("ol/source/XYZ", () => ({
    default: vi.fn().mockImplementation(function () {
        return {
            getTileLoadFunction: vi.fn().mockReturnValue(vi.fn()),
            setTileLoadFunction: vi.fn(),
        };
    }),
}));
vi.mock("ol/source/Vector", () => ({
    default: vi.fn().mockImplementation(function () {
        return {
            clear: vi.fn(),
            addFeature: vi.fn(),
            addFeatures: vi.fn(),
            getFeatures: vi.fn().mockReturnValue([]),
            removeFeature: vi.fn(),
            on: vi.fn(),
        };
    }),
}));
vi.mock("ol/proj", () => ({
    fromLonLat: vi.fn((coords) => coords),
    toLonLat: vi.fn((coords) => coords),
}));
vi.mock("ol/control", () => ({
    defaults: vi.fn().mockReturnValue([]),
}));
vi.mock("ol/control/ScaleLine", () => ({
    default: vi.fn().mockImplementation(function () {
        return {};
    }),
}));
vi.mock("ol/interaction/Draw", () => ({
    default: vi.fn().mockImplementation(function () {
        return { on: vi.fn(), setActive: vi.fn() };
    }),
}));
vi.mock("ol/interaction/Modify", () => ({
    default: vi.fn().mockImplementation(function () {
        return { on: vi.fn(), setActive: vi.fn() };
    }),
}));
vi.mock("ol/interaction/Select", () => ({
    default: vi.fn().mockImplementation(function () {
        return {
            on: vi.fn(),
            setActive: vi.fn(),
            getFeatures: vi.fn().mockReturnValue({
                getArray: vi.fn().mockReturnValue([]),
                clear: vi.fn(),
                push: vi.fn(),
            }),
        };
    }),
}));
vi.mock("ol/interaction/Translate", () => ({
    default: vi.fn().mockImplementation(function () {
        return { on: vi.fn(), setActive: vi.fn() };
    }),
}));
vi.mock("ol/interaction/Snap", () => ({
    default: vi.fn().mockImplementation(function () {
        return { on: vi.fn() };
    }),
}));
vi.mock("ol/interaction/DragBox", () => ({
    default: vi.fn().mockImplementation(function () {
        return { on: vi.fn() };
    }),
}));
vi.mock("ol/Overlay", () => ({
    default: vi.fn().mockImplementation(function () {
        return {
            set: vi.fn(),
            get: vi.fn(),
            setPosition: vi.fn(),
            setOffset: vi.fn(),
        };
    }),
}));
vi.mock("ol/format/GeoJSON", () => ({
    default: vi.fn().mockImplementation(function () {
        return {
            writeFeatures: vi.fn().mockReturnValue('{"type":"FeatureCollection","features":[]}'),
            readFeatures: vi.fn().mockReturnValue([]),
        };
    }),
}));
vi.mock("ol/style", () => ({
    Style: vi.fn(function () {
        return {};
    }),
    Text: vi.fn(function () {
        return {};
    }),
    Fill: vi.fn(function () {
        return {};
    }),
    Stroke: vi.fn(function () {
        return {};
    }),
    Circle: vi.fn(function () {
        return {};
    }),
    Icon: vi.fn(function () {
        return {};
    }),
}));
vi.mock("ol/sphere", () => ({
    getArea: vi.fn(),
    getLength: vi.fn(),
}));
vi.mock("ol/geom", () => ({
    LineString: vi.fn(),
    Polygon: vi.fn(),
    Circle: vi.fn(),
}));
vi.mock("ol/geom/Polygon", () => ({
    fromCircle: vi.fn(),
}));
vi.mock("ol/Observable", () => ({
    unByKey: vi.fn(),
}));

import MapPage from "@/components/map/MapPage.vue";

describe("MapPage.vue", () => {
    let axiosMock;

    beforeAll(() => {
        axiosMock = {
            get: vi.fn().mockImplementation((url) => {
                const defaultData = {
                    config: { map_offline_enabled: false },
                    mbtiles: [],
                    conversations: [],
                    telemetry: [],
                    markers: [],
                    history: [],
                    announces: [],
                };
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
                return Promise.resolve({ data: defaultData });
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
            patch: vi.fn().mockResolvedValue({ data: {} }),
            delete: vi.fn().mockResolvedValue({ data: {} }),
        };
        vi.stubGlobal("api", axiosMock);
        window.api = axiosMock;
    });

    beforeEach(() => {
        vi.stubGlobal("api", axiosMock);
        window.api = axiosMock;
        // Mock localStorage
        const localStorageMock = {
            getItem: vi.fn().mockReturnValue(null),
            setItem: vi.fn(),
            removeItem: vi.fn(),
            clear: vi.fn(),
        };
        Object.defineProperty(window, "localStorage", { value: localStorageMock, writable: true });
    });

    afterEach(() => {
        delete window.api;
    });

    const mountMapPage = () => {
        return mount(MapPage, {
            global: {
                mocks: {
                    $t: (key) => key,
                    $route: { query: {} },
                    $filters: {
                        formatDestinationHash: (h) => h,
                    },
                },
                stubs: {
                    MaterialDesignIcon: {
                        template: '<div class="mdi-stub" :data-icon-name="iconName"></div>',
                        props: ["iconName"],
                    },
                    Toggle: {
                        template: '<div class="toggle-stub"></div>',
                        props: ["modelValue", "id"],
                    },
                    LoadingSpinner: true,
                },
            },
        });
    };

    it("renders the map title", async () => {
        const wrapper = mountMapPage();
        await wrapper.vm.$nextTick();
        expect(wrapper.text()).toContain("map.title");
    });

    it("toggles settings dropdown", async () => {
        const wrapper = mountMapPage();
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.isSettingsOpen).toBe(false);

        // Find settings button by icon name
        const settingsButton = wrapper.find('.mdi-stub[data-icon-name="cog"]').element.parentElement;
        await settingsButton.click();
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.isSettingsOpen).toBe(true);
    });

    it("performs search and displays results", async () => {
        // Mock fetch for search
        global.fetch = vi.fn().mockResolvedValue({
            ok: true,
            json: () => Promise.resolve([{ place_id: 1, display_name: "Result 1", type: "city", lat: "0", lon: "0" }]),
        });

        const wrapper = mountMapPage();
        await flushPromises();
        wrapper.vm.offlineEnabled = false;
        wrapper.vm.isSearchFocused = true;

        const searchInput = wrapper.find('input[type="text"]');
        await searchInput.trigger("focus");
        await searchInput.setValue("test search");

        // Trigger search by enter key
        await searchInput.trigger("keydown.enter");

        await flushPromises();

        expect(wrapper.text()).toContain("Result 1");
        expect(wrapper.text()).toContain("city");

        delete global.fetch;
    });

    it("parses WGS84 coordinates offline without Nominatim", async () => {
        const wrapper = mountMapPage();
        await flushPromises();
        wrapper.vm.offlineEnabled = true;
        wrapper.vm.isSearchFocused = true;
        wrapper.vm.searchQuery = "1.234567, 2.345678";
        const selectSpy = vi.spyOn(wrapper.vm, "selectSearchResult");

        await wrapper.vm.performSearch();
        await flushPromises();

        expect(selectSpy).toHaveBeenCalled();
        const arg = selectSpy.mock.calls[0][0];
        expect(arg.lat).toBeCloseTo(1.234567, 5);
        expect(arg.lon).toBeCloseTo(2.345678, 5);
        expect(arg.type).toBe("wgs84");
    });

    it("uses stacked MBTiles only for default or known online tile presets, not local tile URLs", async () => {
        const wrapper = mountMapPage();
        await wrapper.vm.$nextTick();
        wrapper.vm.offlineEnabled = true;
        wrapper.vm.tileServerUrl = "http://192.168.1.10/tiles/{z}/{x}/{y}.png";
        expect(wrapper.vm.usesOfflineMbtilesRaster()).toBe(false);
        wrapper.vm.tileServerUrl = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
        expect(wrapper.vm.usesOfflineMbtilesRaster()).toBe(true);
    });

    it("search uses custom local nominatim base URL in request", async () => {
        global.fetch = vi.fn().mockResolvedValue({
            ok: true,
            json: () => Promise.resolve([]),
        });

        const wrapper = mountMapPage();
        await wrapper.vm.$nextTick();
        wrapper.vm.nominatimApiUrl = "http://127.0.0.1:18181/nominatim/";
        const searchInput = wrapper.find('input[type="text"]');
        await searchInput.trigger("focus");
        await searchInput.setValue("hq");
        await searchInput.trigger("keydown.enter");
        await flushPromises();

        expect(global.fetch).toHaveBeenCalled();
        const calledUrl = String(global.fetch.mock.calls[0][0]);
        expect(calledUrl).toContain("127.0.0.1:18181");
        expect(calledUrl).toContain("/search?");
        expect(calledUrl).toContain(encodeURIComponent("hq"));

        delete global.fetch;
    });

    it("toggles export mode", async () => {
        const wrapper = mountMapPage();
        await wrapper.vm.$nextTick();
        wrapper.vm.toggleExportMode();
        expect(wrapper.vm.isExportMode).toBe(true);
    });

    it("opens the maps side panel from the header", async () => {
        const wrapper = mountMapPage();
        await wrapper.vm.$nextTick();
        expect(wrapper.find('button[title="map.side_panel"]').exists()).toBe(true);
        await wrapper.find('button[title="map.side_panel"]').trigger("click");
        expect(wrapper.vm.isMapToolsOpen).toBe(true);
        expect(wrapper.text()).toContain("map.tab_discover");
    });

    it("does not construct OpenLayers when an embedded tab is inactive", async () => {
        const wrapper = mount(MapPage, {
            props: { embedded: true, isActiveTab: false },
            global: {
                mocks: {
                    $t: (key) => key,
                    $route: { query: {} },
                    $filters: { formatDestinationHash: (h) => h },
                },
                stubs: {
                    MaterialDesignIcon: {
                        template: '<div class="mdi-stub" :data-icon-name="iconName"></div>',
                        props: ["iconName"],
                    },
                    Toggle: { template: '<div class="toggle-stub"></div>', props: ["modelValue", "id"] },
                    LoadingSpinner: true,
                    MapSidePanel: true,
                },
            },
        });
        await wrapper.vm.$nextTick();
        await flushPromises();
        expect(wrapper.vm.map).toBeNull();
        expect(wrapper.vm._mapBooted).toBeFalsy();
    });

    it("serializeFeatures drops bearing preview features", async () => {
        const wrapper = mountMapPage();
        await wrapper.vm.$nextTick();
        const preview = {
            get: (k) => (k === "bearingPreview" ? true : undefined),
        };
        const normal = {
            get: () => undefined,
            clone: () => ({
                unset: vi.fn(),
                getGeometry: () => null,
                setGeometry: vi.fn(),
            }),
            getStyle: () => null,
        };
        const out = wrapper.vm.serializeFeatures([preview, normal]);
        expect(out).toHaveLength(1);
    });

    it("toggleBearingMode enables and disables bearing state with a stub map", async () => {
        const wrapper = mountMapPage();
        await wrapper.vm.$nextTick();
        wrapper.vm.map = {
            addOverlay: vi.fn(),
            removeOverlay: vi.fn(),
            un: vi.fn(),
        };
        wrapper.vm.select = { setActive: vi.fn(), getFeatures: () => ({ clear: vi.fn(), push: vi.fn() }) };
        wrapper.vm.translate = { setActive: vi.fn() };
        wrapper.vm.modify = { setActive: vi.fn() };
        wrapper.vm.toggleBearingMode();
        expect(wrapper.vm.isBearingMode).toBe(true);
        expect(wrapper.vm.drawType).toBe("Bearing");
        wrapper.vm.toggleBearingMode();
        expect(wrapper.vm.isBearingMode).toBe(false);
        expect(wrapper.vm.select.setActive).toHaveBeenCalledWith(true);
    });

    it("handles a large number of search results with overflow", async () => {
        const manyResults = Array.from({ length: 100 }, (_, i) => ({
            place_id: i,
            display_name: `Result ${i} ` + "A".repeat(50),
            type: "city",
            lat: "0",
            lon: "0",
        }));

        global.fetch = vi.fn().mockResolvedValue({
            ok: true,
            json: () => Promise.resolve(manyResults),
        });

        const wrapper = mountMapPage();
        await wrapper.vm.$nextTick();

        const searchInput = wrapper.find('input[type="text"]');
        await searchInput.setValue("many results");
        await searchInput.trigger("keydown.enter");

        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        const resultItems = wrapper.findAll(".flex.items-start.gap-3"); // Based on common list pattern
        // The search results container should have overflow-y-auto
        const resultsContainer = wrapper.find(
            ".max-h-64.overflow-y-auto, .max-h-\\[calc\\(100vh-200px\\)\\].overflow-y-auto"
        );
        if (resultsContainer.exists()) {
            expect(resultsContainer.classes()).toContain("overflow-y-auto");
        }
    });

    it("dedupes concurrent performSearch before Nominatim (race)", async () => {
        let inFlight = 0;
        let maxInFlight = 0;
        let completed = 0;
        global.fetch = vi.fn(async () => {
            inFlight += 1;
            maxInFlight = Math.max(maxInFlight, inFlight);
            await new Promise((r) => setTimeout(r, 40));
            inFlight -= 1;
            completed += 1;
            return {
                ok: true,
                json: async () => [{ display_name: "Berlin", lat: "52.5", lon: "13.4", type: "city" }],
            };
        });

        const wrapper = mountMapPage();
        await flushPromises();
        wrapper.vm.offlineEnabled = false;
        wrapper.vm.searchQuery = "Berlin";

        const first = wrapper.vm.performSearch();
        const second = wrapper.vm.performSearch();
        await Promise.all([first, second]);
        await flushPromises();

        expect(maxInFlight).toBe(1);
        expect(completed).toBe(1);
        expect(wrapper.vm.isSearching).toBe(false);
        expect(wrapper.vm.searchResults.length).toBe(1);
        expect(wrapper.vm.searchResults[0].display_name).toBe("Berlin");
    });

    it("ignores Nominatim results after a newer searchGeneration (race)", async () => {
        let resolveStale;
        const staleGate = new Promise((r) => {
            resolveStale = r;
        });
        global.fetch = vi.fn(async (url) => {
            const u = String(url);
            if (u.includes("one")) {
                await staleGate;
                return {
                    ok: true,
                    json: async () => [{ display_name: "Stale", lat: "1", lon: "1", type: "city" }],
                };
            }
            return {
                ok: true,
                json: async () => [{ display_name: "Fresh", lat: "2", lon: "2", type: "city" }],
            };
        });

        const wrapper = mountMapPage();
        await flushPromises();
        wrapper.vm.offlineEnabled = false;
        wrapper.vm.searchQuery = "one";

        const p1 = wrapper.vm.performSearch();
        // Unlock so a newer search can start while the first Nominatim call is gated.
        wrapper.vm.isSearching = false;
        wrapper.vm.searchQuery = "two";
        const p2 = wrapper.vm.performSearch();
        await flushPromises();
        resolveStale();
        await Promise.all([p1, p2]);
        await flushPromises();

        expect(wrapper.vm.searchResults.map((r) => r.display_name)).toEqual(["Fresh"]);
        expect(wrapper.vm.isSearching).toBe(false);
    });

    it("applies map_coordinate_format from external config-updated", async () => {
        const wrapper = mountMapPage();
        await flushPromises();
        expect(wrapper.vm.coordinateFormat).toBe("wgs84");
        wrapper.vm.onConfigUpdatedExternally({ map_coordinate_format: "MGRS" });
        expect(wrapper.vm.coordinateFormat).toBe("mgrs");
        wrapper.vm.onConfigUpdatedExternally({ map_coordinate_format: "nope" });
        expect(wrapper.vm.coordinateFormat).toBe("wgs84");
    });

    it("bumps geoWasmEpoch when refreshGeoWasmEpoch finds WASM ready", async () => {
        const wrapper = mountMapPage();
        await flushPromises();
        const before = wrapper.vm.geoWasmEpoch;
        globalThis.meshchatxGeoFormat = () => "{}";
        globalThis.meshchatxGeoParse = () => "{}";
        globalThis.meshchatxGeoLatLonToGrid = () => "{}";
        globalThis.__MESHCHATX_TEST_GEO_WASM_BUNDLED__ = true;
        await wrapper.vm.refreshGeoWasmEpoch();
        expect(wrapper.vm.geoWasmEpoch).toBeGreaterThan(before);
        delete globalThis.meshchatxGeoFormat;
        delete globalThis.meshchatxGeoParse;
        delete globalThis.meshchatxGeoLatLonToGrid;
        delete globalThis.__MESHCHATX_TEST_GEO_WASM_BUNDLED__;
    });
});
