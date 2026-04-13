import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import NetworkVisualiser from "@/components/network-visualiser/NetworkVisualiser.vue";

// Mock vis-network and vis-data
vi.mock("vis-network", () => ({
    Network: vi.fn().mockImplementation(function () {
        return {
            on: vi.fn(),
            off: vi.fn(),
            destroy: vi.fn(),
            setOptions: vi.fn(),
            setData: vi.fn(),
            getPositions: vi.fn().mockReturnValue({ me: { x: 0, y: 0 } }),
        };
    }),
}));

vi.mock("vis-data", () => {
    class MockDataSet {
        constructor() {
            this._data = new Map();
        }
        add(data) {
            (Array.isArray(data) ? data : [data]).forEach((i) => this._data.set(i.id, i));
        }
        update(data) {
            (Array.isArray(data) ? data : [data]).forEach((i) => this._data.set(i.id, i));
        }
        remove(ids) {
            (Array.isArray(ids) ? ids : [ids]).forEach((id) => this._data.delete(id));
        }
        get(id) {
            return id === undefined ? Array.from(this._data.values()) : this._data.get(id) || null;
        }
        getIds() {
            return Array.from(this._data.keys());
        }
        get length() {
            return this._data.size;
        }
    }
    return { DataSet: MockDataSet };
});

describe("NetworkVisualiser Optimization and Abort", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn().mockImplementation((url) => {
                if (url.includes("/api/v1/config")) return Promise.resolve({ data: { config: {} } });
                if (url.includes("/api/v1/interface-stats"))
                    return Promise.resolve({ data: { interface_stats: { interfaces: [] } } });
                if (url.includes("/api/v1/lxmf/conversations")) return Promise.resolve({ data: { conversations: [] } });
                if (url.includes("/api/v1/path-table"))
                    return Promise.resolve({ data: { path_table: [], total_count: 0 } });
                if (url.includes("/api/v1/announces"))
                    return Promise.resolve({ data: { announces: [], total_count: 0 } });
                return Promise.resolve({ data: {} });
            }),
            isCancel: vi.fn().mockImplementation((e) => e && e.name === "AbortError"),
        };
        window.api = axiosMock;

        // Mock URL methods
        global.URL.createObjectURL = vi.fn().mockReturnValue("blob:mock");
        global.URL.revokeObjectURL = vi.fn();
    });

    afterEach(() => {
        delete window.api;
        vi.clearAllMocks();
    });

    const mountVisualiser = () => {
        return mount(NetworkVisualiser, {
            global: {
                mocks: { $t: (msg) => msg },
                stubs: { Toggle: true },
            },
        });
    };

    it("aborts pending requests on unmount", async () => {
        // Prevent auto-init
        vi.spyOn(NetworkVisualiser.methods, "init").mockImplementation(() => {});
        const wrapper = mountVisualiser();

        const abortSpy = vi.spyOn(wrapper.vm.abortController, "abort");

        let signal;
        axiosMock.get.mockImplementationOnce((url, config) => {
            signal = config.signal;
            return new Promise(() => {});
        });

        wrapper.vm.getPathTableBatch();

        expect(axiosMock.get).toHaveBeenCalled();
        expect(signal.aborted).toBe(false);

        wrapper.unmount();

        expect(abortSpy).toHaveBeenCalled();
        expect(signal.aborted).toBe(true);
    });

    it("stops processing visualization batches when aborted", async () => {
        vi.spyOn(NetworkVisualiser.methods, "init").mockImplementation(() => {});
        const wrapper = mountVisualiser();

        // Prepare large data
        wrapper.vm.pathTable = Array.from({ length: 1000 }, (_, i) => ({ hash: `h${i}`, interface: "eth0", hops: 1 }));
        wrapper.vm.announces = wrapper.vm.pathTable.reduce((acc, cur) => {
            acc[cur.hash] = {
                destination_hash: cur.hash,
                aspect: "lxmf.delivery",
                display_name: "node",
            };
            return acc;
        }, {});

        // Add lxmf_user_icon to trigger await in createIconImage and slow it down
        const firstHash = wrapper.vm.pathTable[0].hash;
        wrapper.vm.announces[firstHash].lxmf_user_icon = {
            icon_name: "test",
            foreground_colour: "#000",
            background_colour: "#fff",
        };
        wrapper.vm.conversations[firstHash] = { lxmf_user_icon: wrapper.vm.announces[firstHash].lxmf_user_icon };

        // Mock createIconImage to be slow
        wrapper.vm.createIconImage = vi.fn().mockImplementation(() => new Promise((r) => setTimeout(r, 100)));

        const processPromise = wrapper.vm.processVisualization();

        // Give it some time to start first batch and hit the await
        await new Promise((r) => setTimeout(r, 50));

        // It should be in batch 1 and stuck on createIconImage
        expect(wrapper.vm.currentBatch).toBe(1);

        // Abort
        wrapper.vm.abortController.abort();

        await processPromise;

        // Should have aborted and not reached the end where it resets currentBatch to 0
        // (Wait, actually if it returns early it stays 1)
        expect(wrapper.vm.currentBatch).toBe(1);
    });

    it("parallelizes batch fetching", async () => {
        vi.spyOn(NetworkVisualiser.methods, "init").mockImplementation(() => {});
        const wrapper = mountVisualiser();

        // Mock success with total_count > pageSize
        axiosMock.get.mockImplementation((url, config) => {
            if (url === "/api/v1/path-table") {
                return Promise.resolve({ data: { path_table: [], total_count: 5000 } });
            }
            return Promise.resolve({ data: {} });
        });

        wrapper.vm.pageSize = 1000;

        await wrapper.vm.getPathTableBatch();

        // Should have called offset 0, then offsets 1000, 2000, 3000, 4000
        // Total 5 calls
        expect(axiosMock.get).toHaveBeenCalledTimes(5);
    });

    it("applies LOD based on scale", async () => {
        vi.spyOn(NetworkVisualiser.methods, "init").mockImplementation(() => {});
        const wrapper = mountVisualiser();
        wrapper.vm.network = {
            getScale: vi.fn(),
        };

        const testNode = { id: "test", label: "Test Label", _originalSize: 25, _originalShape: "circularImage" };
        wrapper.vm.nodes.add(testNode);

        // Test Low LOD
        wrapper.vm.network.getScale.mockReturnValue(0.1);
        wrapper.vm.updateLOD();
        expect(wrapper.vm.currentLOD).toBe("low");
        let updatedNode = wrapper.vm.nodes.get("test");
        expect(updatedNode.shape).toBe("dot");
        expect(updatedNode.font.size).toBe(0);

        // Test Medium LOD
        wrapper.vm.network.getScale.mockReturnValue(0.3);
        wrapper.vm.updateLOD();
        expect(wrapper.vm.currentLOD).toBe("medium");
        updatedNode = wrapper.vm.nodes.get("test");
        expect(updatedNode.shape).toBe("circularImage");
        expect(updatedNode.font.size).toBe(0);

        // Test High LOD
        wrapper.vm.network.getScale.mockReturnValue(0.7);
        wrapper.vm.updateLOD();
        expect(wrapper.vm.currentLOD).toBe("high");
        updatedNode = wrapper.vm.nodes.get("test");
        expect(updatedNode.shape).toBe("circularImage");
        expect(updatedNode.font.size).toBe(11);
    });

    it("clears Blob URLs from icon cache on unmount", async () => {
        vi.spyOn(NetworkVisualiser.methods, "init").mockImplementation(() => {});
        const wrapper = mountVisualiser();

        const mockBlobUrl = "blob:mock-url-1";
        wrapper.vm.iconCache["test-key"] = mockBlobUrl;

        const revokeSpy = vi.spyOn(URL, "revokeObjectURL");

        wrapper.unmount();

        expect(revokeSpy).toHaveBeenCalledWith(mockBlobUrl);
        expect(Object.keys(wrapper.vm.iconCache).length).toBe(0);
    });

    it("performance: LOD update time for 2000 nodes", async () => {
        vi.spyOn(NetworkVisualiser.methods, "init").mockImplementation(() => {});
        const wrapper = mountVisualiser();
        wrapper.vm.network = { getScale: vi.fn() };

        const nodeCount = 2000;
        const nodes = Array.from({ length: nodeCount }, (_, i) => ({
            id: `n${i}`,
            label: `Node ${i}`,
            _originalSize: 25,
            _originalShape: "circularImage",
        }));
        wrapper.vm.nodes.add(nodes);

        const start = performance.now();
        wrapper.vm.network.getScale.mockReturnValue(0.1); // Switch to low LOD
        wrapper.vm.updateLOD();
        const end = performance.now();

        console.log(`LOD update for ${nodeCount} nodes took ${(end - start).toFixed(2)}ms`);
        expect(end - start).toBeLessThan(100); // Should be very fast
    });

    it("reuses one cached icon for 500 nodes with identical lxmf_user_icon", async () => {
        vi.spyOn(NetworkVisualiser.methods, "init").mockImplementation(() => {});
        const wrapper = mountVisualiser();

        // Setup 500 nodes with the same icon
        const iconInfo = { icon_name: "test", foreground_colour: "#000", background_colour: "#fff" };
        wrapper.vm.pathTable = Array.from({ length: 500 }, (_, i) => ({ hash: `h${i}`, interface: "eth0", hops: 1 }));
        wrapper.vm.announces = wrapper.vm.pathTable.reduce((acc, cur) => {
            acc[cur.hash] = {
                destination_hash: cur.hash,
                aspect: "lxmf.delivery",
                display_name: "node",
                lxmf_user_icon: iconInfo,
            };
            return acc;
        }, {});
        wrapper.vm.conversations = wrapper.vm.pathTable.reduce((acc, cur) => {
            acc[cur.hash] = { lxmf_user_icon: iconInfo };
            return acc;
        }, {});

        wrapper.vm.createIconImage = vi.fn(async function (iconName, foregroundColor, backgroundColor, size = 64) {
            const cacheKey = `${iconName}-${foregroundColor}-${backgroundColor}-${size}`;
            if (this.iconCache[cacheKey]) {
                return this.iconCache[cacheKey];
            }
            await new Promise((r) => setTimeout(r, 0));
            const url = "blob:mock-icon";
            this.iconCache[cacheKey] = url;
            return url;
        });

        await wrapper.vm.processVisualization();
        expect(wrapper.vm.createIconImage).toHaveBeenCalledTimes(1);

        await wrapper.vm.processVisualization();
        expect(wrapper.vm.createIconImage).toHaveBeenCalledTimes(1);
    });
});
