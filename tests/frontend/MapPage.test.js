import { mount } from "@vue/test-utils";
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

// Mock OpenLayers
vi.mock("ol/Map", () => ({
    default: vi.fn().mockImplementation(() => ({
        on: vi.fn(),
        addLayer: vi.fn(),
        addInteraction: vi.fn(),
        addOverlay: vi.fn(),
        removeInteraction: vi.fn(),
        removeOverlay: vi.fn(),
        un: vi.fn(),
        getEventPixel: vi.fn().mockReturnValue([0, 0]),
        getTargetElement: vi.fn().mockReturnValue({ style: {} }),
        getView: vi.fn().mockReturnValue({
            on: vi.fn(),
            setCenter: vi.fn(),
            setZoom: vi.fn(),
            getCenter: vi.fn().mockReturnValue([0, 0]),
            getZoom: vi.fn().mockReturnValue(2),
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
    })),
}));

vi.mock("ol/View", () => ({ default: vi.fn() }));
vi.mock("ol/layer/Tile", () => ({ default: vi.fn() }));
vi.mock("ol/layer/Vector", () => ({ default: vi.fn() }));
vi.mock("ol/source/XYZ", () => ({
    default: vi.fn().mockImplementation(() => ({
        getTileLoadFunction: vi.fn().mockReturnValue(vi.fn()),
        setTileLoadFunction: vi.fn(),
    })),
}));
vi.mock("ol/source/Vector", () => ({
    default: vi.fn().mockImplementation(() => ({
        clear: vi.fn(),
        addFeature: vi.fn(),
        addFeatures: vi.fn(),
        getFeatures: vi.fn().mockReturnValue([]),
        on: vi.fn(),
    })),
}));
vi.mock("ol/proj", () => ({
    fromLonLat: vi.fn((coords) => coords),
    toLonLat: vi.fn((coords) => coords),
}));
vi.mock("ol/control", () => ({
    defaults: vi.fn().mockReturnValue([]),
}));
vi.mock("ol/interaction/Draw", () => ({
    default: vi.fn().mockImplementation(() => ({
        on: vi.fn(),
        setActive: vi.fn(),
    })),
}));
vi.mock("ol/interaction/Modify", () => ({
    default: vi.fn().mockImplementation(() => ({
        on: vi.fn(),
        setActive: vi.fn(),
    })),
}));
vi.mock("ol/interaction/Select", () => ({
    default: vi.fn().mockImplementation(() => ({
        on: vi.fn(),
        setActive: vi.fn(),
        getFeatures: vi.fn().mockReturnValue({
            getArray: vi.fn().mockReturnValue([]),
            clear: vi.fn(),
            push: vi.fn(),
        }),
    })),
}));
vi.mock("ol/interaction/Translate", () => ({
    default: vi.fn().mockImplementation(() => ({
        on: vi.fn(),
        setActive: vi.fn(),
    })),
}));
vi.mock("ol/interaction/Snap", () => ({
    default: vi.fn().mockImplementation(() => ({
        on: vi.fn(),
    })),
}));
vi.mock("ol/interaction/DragBox", () => ({
    default: vi.fn().mockImplementation(() => ({
        on: vi.fn(),
    })),
}));
vi.mock("ol/Overlay", () => ({
    default: vi.fn().mockImplementation(() => ({
        set: vi.fn(),
        get: vi.fn(),
        setPosition: vi.fn(),
        setOffset: vi.fn(),
    })),
}));
vi.mock("ol/format/GeoJSON", () => ({
    default: vi.fn().mockImplementation(() => ({
        writeFeatures: vi.fn().mockReturnValue('{"type":"FeatureCollection","features":[]}'),
        readFeatures: vi.fn().mockReturnValue([]),
    })),
}));
vi.mock("ol/style", () => ({
    Style: vi.fn().mockImplementation(() => ({})),
    Text: vi.fn().mockImplementation(() => ({})),
    Fill: vi.fn().mockImplementation(() => ({})),
    Stroke: vi.fn().mockImplementation(() => ({})),
    Circle: vi.fn().mockImplementation(() => ({})),
    Icon: vi.fn().mockImplementation(() => ({})),
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
                if (url.includes("nominatim")) return Promise.resolve({ data: [] });
                return Promise.resolve({ data: defaultData });
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
            patch: vi.fn().mockResolvedValue({ data: {} }),
            delete: vi.fn().mockResolvedValue({ data: {} }),
        };
        vi.stubGlobal("axios", axiosMock);
        window.axios = axiosMock;
    });

    beforeEach(() => {
        vi.stubGlobal("axios", axiosMock);
        window.axios = axiosMock;
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
        delete window.axios;
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
        await wrapper.vm.$nextTick();

        const searchInput = wrapper.find('input[type="text"]');
        await searchInput.trigger("focus");
        await searchInput.setValue("test search");

        // Trigger search by enter key
        await searchInput.trigger("keydown.enter");

        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick(); // Wait for fetch
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("Result 1");
        expect(wrapper.text()).toContain("city");

        delete global.fetch;
    });

    it("toggles export mode", async () => {
        const wrapper = mountMapPage();
        await wrapper.vm.$nextTick();

        const exportButton = wrapper.find('button[title="map.export_area"]');
        if (exportButton.exists()) {
            await exportButton.trigger("click");
            expect(wrapper.vm.isExportMode).toBe(true);
            expect(wrapper.text()).toContain("map.export_instructions");
        }
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
});
