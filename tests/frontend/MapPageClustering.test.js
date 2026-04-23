import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach, beforeAll } from "vitest";

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

const viewMock = {
    on: vi.fn(),
    setCenter: vi.fn(),
    setZoom: vi.fn(),
    getCenter: vi.fn().mockReturnValue([0, 0]),
    getZoom: vi.fn().mockReturnValue(8),
    getMaxZoom: vi.fn().mockReturnValue(19),
    getResolution: vi.fn().mockReturnValue(10),
    fit: vi.fn(),
    animate: vi.fn(),
};

const mapMock = {
    on: vi.fn(),
    addLayer: vi.fn(),
    addInteraction: vi.fn(),
    addOverlay: vi.fn(),
    removeInteraction: vi.fn(),
    removeOverlay: vi.fn(),
    un: vi.fn(),
    getEventPixel: vi.fn().mockReturnValue([0, 0]),
    getTargetElement: vi.fn().mockReturnValue({ style: {} }),
    getView: vi.fn().mockReturnValue(viewMock),
    getLayers: vi.fn().mockReturnValue({
        clear: vi.fn(),
        push: vi.fn(),
        getArray: vi.fn().mockReturnValue([]),
    }),
    getOverlays: vi.fn().mockReturnValue({ getArray: vi.fn().mockReturnValue([]) }),
    forEachFeatureAtPixel: vi.fn(),
    setTarget: vi.fn(),
    updateSize: vi.fn(),
    getViewport: vi.fn().mockReturnValue({
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
    }),
};

vi.mock("ol/Map", () => ({
    default: vi.fn().mockImplementation(function () {
        return mapMock;
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
vi.mock("ol/control", () => ({ defaults: vi.fn().mockReturnValue([]) }));
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
        return { set: vi.fn(), get: vi.fn(), setPosition: vi.fn(), setOffset: vi.fn() };
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
vi.mock("ol/sphere", () => ({ getArea: vi.fn(), getLength: vi.fn() }));
vi.mock("ol/geom", () => ({ LineString: vi.fn(), Polygon: vi.fn(), Circle: vi.fn() }));
vi.mock("ol/geom/Polygon", () => ({ fromCircle: vi.fn() }));
vi.mock("ol/Observable", () => ({ unByKey: vi.fn() }));

import MapPage from "@/components/map/MapPage.vue";

/**
 * Build a lightweight mock OpenLayers feature so we can assert on cluster
 * methods without spinning up real OpenLayers geometries. Mirrors the
 * surface area used by MapPage (get/getGeometry/.getCoordinates).
 */
function makeMockFeature(props, coord) {
    const geometry = coord ? { getCoordinates: () => coord } : null;
    return {
        get: (key) => props[key],
        set: (key, value) => {
            props[key] = value;
        },
        getGeometry: () => geometry,
    };
}

function makeClusterFeature(items, centerCoord = [0, 0]) {
    const props = {
        cluster: true,
        clusterCount: items.length,
        clusterItems: items,
        originalCoord: centerCoord,
    };
    return makeMockFeature(props, centerCoord);
}

describe("MapPage cluster behaviour", () => {
    let axiosMock;

    beforeAll(() => {
        axiosMock = {
            get: vi.fn().mockImplementation((url) => {
                if (url.includes("/api/v1/config"))
                    return Promise.resolve({ data: { config: { map_offline_enabled: false } } });
                if (url.includes("/api/v1/map/mbtiles")) return Promise.resolve({ data: [] });
                if (url.includes("/api/v1/lxmf/conversations")) return Promise.resolve({ data: { conversations: [] } });
                if (url.includes("/api/v1/telemetry/peers")) return Promise.resolve({ data: { telemetry: [] } });
                if (url.includes("/api/v1/telemetry/markers")) return Promise.resolve({ data: { markers: [] } });
                if (url.includes("/api/v1/map/offline")) return Promise.resolve({ data: {} });
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

    beforeEach(() => {
        viewMock.fit.mockClear();
        viewMock.animate.mockClear();
        viewMock.setCenter.mockClear();
        viewMock.setZoom.mockClear();
        viewMock.getZoom.mockReturnValue(8);
        viewMock.getResolution.mockReturnValue(10);
        viewMock.getMaxZoom.mockReturnValue(19);

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

    const mountMapPage = async () => {
        const wrapper = mount(MapPage, {
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
                },
            },
        });
        await wrapper.vm.$nextTick();
        wrapper.vm.map = mapMock;
        return wrapper;
    };

    describe("extentDiagonal", () => {
        it("returns 0 for empty/invalid extents", async () => {
            const wrapper = await mountMapPage();
            expect(wrapper.vm.extentDiagonal(null)).toBe(0);
            expect(wrapper.vm.extentDiagonal([])).toBe(0);
            expect(wrapper.vm.extentDiagonal([Infinity, Infinity, -Infinity, -Infinity])).toBe(0);
        });

        it("computes the diagonal length for a normal extent", async () => {
            const wrapper = await mountMapPage();
            expect(wrapper.vm.extentDiagonal([0, 0, 3, 4])).toBeCloseTo(5);
            expect(wrapper.vm.extentDiagonal([10, 10, 10, 10])).toBe(0);
        });
    });

    describe("buildClusterItems", () => {
        it("returns an empty list for a missing feature", async () => {
            const wrapper = await mountMapPage();
            expect(wrapper.vm.buildClusterItems(null)).toEqual([]);
        });

        it("normalises telemetry, discovered, and unknown items", async () => {
            const wrapper = await mountMapPage();
            const tFeature = makeMockFeature(
                {
                    telemetry: { destination_hash: "abcd1234ef" },
                    peer: { display_name: "Alice" },
                    originalCoord: [10, 20],
                },
                [10, 20]
            );
            const dFeature = makeMockFeature(
                {
                    discovered: { name: "RNode-7", interface: "AutoInterface", type: "rnode" },
                    originalCoord: [11, 21],
                },
                [11, 21]
            );
            const unknownFeature = makeMockFeature({ originalCoord: [12, 22] }, [12, 22]);
            const cluster = makeClusterFeature([tFeature, dFeature, unknownFeature], [11, 21]);

            const items = wrapper.vm.buildClusterItems(cluster);
            expect(items).toHaveLength(3);
            expect(items[0]).toMatchObject({ kind: "telemetry", label: "Alice", identifier: "abcd1234ef" });
            expect(items[0].coord).toEqual([10, 20]);
            expect(items[1]).toMatchObject({
                kind: "discovered",
                label: "RNode-7",
                identifier: "AutoInterface",
            });
            expect(items[2].kind).toBe("unknown");
        });

        it("falls back to a truncated hash when no peer name is set", async () => {
            const wrapper = await mountMapPage();
            const tFeature = makeMockFeature({ telemetry: { destination_hash: "deadbeefcafe" } }, [0, 0]);
            const cluster = makeClusterFeature([tFeature]);
            const items = wrapper.vm.buildClusterItems(cluster);
            expect(items[0].label).toBe("deadbeef");
        });
    });

    describe("zoomToCluster", () => {
        it("does nothing when the cluster is empty", async () => {
            const wrapper = await mountMapPage();
            const empty = makeClusterFeature([]);
            wrapper.vm.zoomToCluster(empty);
            expect(viewMock.fit).not.toHaveBeenCalled();
            expect(viewMock.animate).not.toHaveBeenCalled();
        });

        it("calls view.fit with the bounding extent for spread items", async () => {
            const wrapper = await mountMapPage();
            const items = [
                makeMockFeature({ originalCoord: [0, 0] }, [0, 0]),
                makeMockFeature({ originalCoord: [10000, 10000] }, [10000, 10000]),
            ];
            const cluster = makeClusterFeature(items);
            wrapper.vm.zoomToCluster(cluster);
            expect(viewMock.fit).toHaveBeenCalledTimes(1);
            const [extent, opts] = viewMock.fit.mock.calls[0];
            expect(extent[0]).toBeCloseTo(0);
            expect(extent[2]).toBeCloseTo(10000);
            expect(opts.maxZoom).toBeLessThanOrEqual(19);
            expect(opts.padding).toEqual([80, 80, 80, 80]);
        });

        it("animates to the centre when every item shares the same coord", async () => {
            const wrapper = await mountMapPage();
            const items = [
                makeMockFeature({ originalCoord: [500, 500] }, [500, 500]),
                makeMockFeature({ originalCoord: [500, 500] }, [500, 500]),
                makeMockFeature({ originalCoord: [500, 500] }, [500, 500]),
            ];
            const cluster = makeClusterFeature(items, [500, 500]);
            wrapper.vm.zoomToCluster(cluster);
            expect(viewMock.fit).not.toHaveBeenCalled();
            expect(viewMock.animate).toHaveBeenCalledTimes(1);
            const animateOpts = viewMock.animate.mock.calls[0][0];
            expect(animateOpts.center).toEqual([500, 500]);
            expect(animateOpts.zoom).toBe(12); // 8 + 4
        });

        it("clamps the zoom to the view's maxZoom", async () => {
            viewMock.getZoom.mockReturnValue(18);
            viewMock.getMaxZoom.mockReturnValue(19);
            const wrapper = await mountMapPage();
            const items = [makeMockFeature({ originalCoord: [0, 0] }, [0, 0])];
            const cluster = makeClusterFeature(items, [0, 0]);
            wrapper.vm.zoomToCluster(cluster);
            const animateOpts = viewMock.animate.mock.calls[0][0];
            expect(animateOpts.zoom).toBe(19);
        });

        it("treats a sub-resolution extent as degenerate", async () => {
            viewMock.getResolution.mockReturnValue(50);
            const wrapper = await mountMapPage();
            const items = [
                makeMockFeature({ originalCoord: [0, 0] }, [0, 0]),
                makeMockFeature({ originalCoord: [5, 5] }, [5, 5]),
            ];
            const cluster = makeClusterFeature(items, [2.5, 2.5]);
            wrapper.vm.zoomToCluster(cluster);
            expect(viewMock.fit).not.toHaveBeenCalled();
            expect(viewMock.animate).toHaveBeenCalledTimes(1);
        });

        it("falls back to setCenter/setZoom when animate is missing", async () => {
            viewMock.animate = undefined;
            const wrapper = await mountMapPage();
            const items = [
                makeMockFeature({ originalCoord: [100, 200] }, [100, 200]),
                makeMockFeature({ originalCoord: [100, 200] }, [100, 200]),
            ];
            const cluster = makeClusterFeature(items, [100, 200]);
            wrapper.vm.zoomToCluster(cluster);
            expect(viewMock.setCenter).toHaveBeenCalledWith([100, 200]);
            expect(viewMock.setZoom).toHaveBeenCalledWith(12);
            viewMock.animate = vi.fn();
        });
    });

    describe("openCluster", () => {
        it("populates selectedCluster, clears selectedMarker, and zooms", async () => {
            const wrapper = await mountMapPage();
            wrapper.vm.selectedMarker = { telemetry: { destination_hash: "x" } };
            const items = [
                makeMockFeature(
                    {
                        telemetry: { destination_hash: "abcd1234" },
                        peer: { display_name: "Alice" },
                        originalCoord: [0, 0],
                    },
                    [0, 0]
                ),
                makeMockFeature(
                    {
                        discovered: { name: "Node A", interface: "AutoIf" },
                        originalCoord: [10, 10],
                    },
                    [10, 10]
                ),
            ];
            const cluster = makeClusterFeature(items, [5, 5]);
            wrapper.vm.openCluster(cluster);
            expect(wrapper.vm.selectedMarker).toBeNull();
            expect(wrapper.vm.selectedCluster).not.toBeNull();
            expect(wrapper.vm.selectedCluster.count).toBe(2);
            expect(wrapper.vm.selectedCluster.items).toHaveLength(2);
            expect(viewMock.fit).toHaveBeenCalledTimes(1);
        });

        it("ignores nullish features", async () => {
            const wrapper = await mountMapPage();
            wrapper.vm.openCluster(null);
            expect(wrapper.vm.selectedCluster).toBeNull();
            expect(viewMock.fit).not.toHaveBeenCalled();
        });
    });

    describe("selectClusterItem", () => {
        it("opens the underlying marker and closes the cluster panel", async () => {
            const wrapper = await mountMapPage();
            const discovered = { name: "Node B", interface: "RNode", latitude: 1, longitude: 2 };
            const innerFeature = makeMockFeature({ discovered, originalCoord: [42, 24] }, [42, 24]);
            wrapper.vm.selectedCluster = {
                count: 1,
                items: [
                    {
                        feature: innerFeature,
                        kind: "discovered",
                        label: "Node B",
                        identifier: "RNode",
                        coord: [42, 24],
                        discovered,
                    },
                ],
            };
            wrapper.vm.selectClusterItem(wrapper.vm.selectedCluster.items[0]);
            expect(wrapper.vm.selectedCluster).toBeNull();
            expect(wrapper.vm.selectedMarker).toMatchObject({ discovered });
            expect(viewMock.animate).toHaveBeenCalledWith(expect.objectContaining({ center: [42, 24] }));
        });

        it("does not animate when the item has no coordinate", async () => {
            const wrapper = await mountMapPage();
            const discovered = { name: "Node C", latitude: 0, longitude: 0 };
            const innerFeature = makeMockFeature({ discovered }, null);
            wrapper.vm.selectClusterItem({
                feature: innerFeature,
                kind: "discovered",
                label: "Node C",
                discovered,
            });
            expect(viewMock.animate).not.toHaveBeenCalled();
            expect(wrapper.vm.selectedMarker).not.toBeNull();
        });

        it("is a no-op when the item or feature is missing", async () => {
            const wrapper = await mountMapPage();
            wrapper.vm.selectedCluster = { count: 0, items: [] };
            wrapper.vm.selectClusterItem(null);
            wrapper.vm.selectClusterItem({});
            expect(wrapper.vm.selectedCluster).not.toBeNull();
        });
    });

    describe("closeClusterPanel", () => {
        it("clears the cluster overlay", async () => {
            const wrapper = await mountMapPage();
            wrapper.vm.selectedCluster = { count: 2, items: [] };
            wrapper.vm.closeClusterPanel();
            expect(wrapper.vm.selectedCluster).toBeNull();
        });
    });
});
