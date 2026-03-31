import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach, beforeAll } from "vitest";
import MapPage from "@/components/map/MapPage.vue";

// Mock TileCache
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

// Mock OpenLayers (Vitest 4: constructor mocks must use function/class, not arrow fns)
vi.mock("ol/Map", () => ({
    default: vi.fn().mockImplementation(function () {
        return {
            on: vi.fn(),
            un: vi.fn(),
            addLayer: vi.fn(),
            removeLayer: vi.fn(),
            addInteraction: vi.fn(),
            removeInteraction: vi.fn(),
            addOverlay: vi.fn(),
            removeOverlay: vi.fn(),
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

describe("MapPage.vue - Drawing and Measurement Tools", () => {
    let axiosMock;

    beforeAll(() => {
        // Mock localStorage
        const localStorageMock = (function () {
            let store = {};
            return {
                getItem: vi.fn((key) => store[key] || null),
                setItem: vi.fn((key, value) => {
                    store[key] = value.toString();
                }),
                clear: vi.fn(() => {
                    store = {};
                }),
                removeItem: vi.fn((key) => {
                    delete store[key];
                }),
            };
        })();
        Object.defineProperty(window, "localStorage", { value: localStorageMock });

        axiosMock = {
            get: vi.fn().mockImplementation((url) => {
                if (url.includes("/api/v1/config"))
                    return Promise.resolve({
                        data: {
                            config: {
                                map_offline_enabled: false,
                                map_default_lat: 0,
                                map_default_lon: 0,
                                map_default_zoom: 2,
                            },
                        },
                    });
                if (url.includes("/api/v1/map/mbtiles")) return Promise.resolve({ data: [] });
                if (url.includes("/api/v1/lxmf/conversations")) return Promise.resolve({ data: { conversations: [] } });
                if (url.includes("/api/v1/telemetry/peers")) return Promise.resolve({ data: { telemetry: [] } });
                if (url.includes("/api/v1/map/drawings")) return Promise.resolve({ data: { drawings: [] } });
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
            patch: vi.fn().mockResolvedValue({ data: {} }),
            delete: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.api = axiosMock;
    });

    const mountMapPage = () => {
        return mount(MapPage, {
            global: {
                directives: {
                    "click-outside": vi.fn(),
                },
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
                    Toggle: true,
                    LoadingSpinner: true,
                },
            },
        });
    };

    it("renders the drawing toolbar", async () => {
        const wrapper = mountMapPage();
        await wrapper.vm.$nextTick();

        const tools = ["Point", "LineString", "Polygon", "Circle"];
        tools.forEach((type) => {
            expect(wrapper.find(`button[title="map.tool_${type.toLowerCase()}"]`).exists()).toBe(true);
        });
        expect(wrapper.find('button[title="map.tool_measure"]').exists()).toBe(true);
        expect(wrapper.find('button[title="map.tool_clear"]').exists()).toBe(true);
    });

    it("toggles drawing tool", async () => {
        const wrapper = mountMapPage();
        await wrapper.vm.$nextTick();
        await new Promise((resolve) => setTimeout(resolve, 50)); // wait for initMap
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.map).toBeDefined();

        const pointTool = wrapper.find('button[title="map.tool_point"]');
        await pointTool.trigger("click");
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.drawType).toBe("Point");
        expect(wrapper.vm.draw).not.toBeNull();

        await pointTool.trigger("click");
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.drawType).toBeNull();
        expect(wrapper.vm.draw).toBeNull();
    });

    it("toggles measurement tool", async () => {
        const wrapper = mountMapPage();
        await wrapper.vm.$nextTick();
        await new Promise((resolve) => setTimeout(resolve, 50)); // wait for initMap
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.map).toBeDefined();

        const measureTool = wrapper.find('button[title="map.tool_measure"]');
        await measureTool.trigger("click");
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.isMeasuring).toBe(true);
        expect(wrapper.vm.drawType).toBe("LineString");

        await measureTool.trigger("click");
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.isMeasuring).toBe(false);
        expect(wrapper.vm.drawType).toBeNull();
    });

    it("opens save drawing modal", async () => {
        const wrapper = mountMapPage();
        await wrapper.vm.$nextTick();

        const saveButton = wrapper.find('button[title="map.save_drawing"]');
        await saveButton.trigger("click");
        expect(wrapper.vm.showSaveDrawingModal).toBe(true);
        expect(wrapper.text()).toContain("map.save_drawing_title");
    });

    it("saves a drawing layer", async () => {
        const wrapper = mountMapPage();
        await wrapper.vm.$nextTick();

        wrapper.vm.showSaveDrawingModal = true;
        wrapper.vm.newDrawingName = "Test Layer";
        await wrapper.vm.$nextTick();

        const saveBtn = wrapper.findAll("button").find((b) => b.text() === "common.save");
        await saveBtn.trigger("click");

        expect(axiosMock.post).toHaveBeenCalledWith(
            "/api/v1/map/drawings",
            expect.objectContaining({
                name: "Test Layer",
            })
        );
        expect(wrapper.vm.showSaveDrawingModal).toBe(false);
    });

    it("opens load drawing modal and lists drawings", async () => {
        const drawings = [{ id: 1, name: "Saved Layer 1", updated_at: new Date().toISOString(), data: "{}" }];
        axiosMock.get.mockImplementation((url) => {
            if (url.includes("/api/v1/map/drawings")) return Promise.resolve({ data: { drawings } });
            if (url.includes("/api/v1/config"))
                return Promise.resolve({ data: { config: { map_offline_enabled: false } } });
            return Promise.resolve({ data: {} });
        });

        const wrapper = mountMapPage();
        await wrapper.vm.$nextTick();
        await new Promise((resolve) => setTimeout(resolve, 10)); // wait for mount logic

        const loadButton = wrapper.find('button[title="map.load_drawing"]');
        await loadButton.trigger("click");

        expect(wrapper.vm.showLoadDrawingModal).toBe(true);
        await wrapper.vm.$nextTick();
        await new Promise((resolve) => setTimeout(resolve, 50)); // Wait for axios and modal render

        expect(wrapper.text()).toContain("Saved Layer 1");
    });
});
