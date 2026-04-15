import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock vis-network
vi.mock("vis-network", () => {
    return {
        Network: vi.fn().mockImplementation(function () {
            return {
                on: vi.fn(),
                off: vi.fn(),
                destroy: vi.fn(),
                setOptions: vi.fn(),
                setData: vi.fn(),
                getPositions: vi.fn(),
                storePositions: vi.fn(),
                fit: vi.fn(),
                focus: vi.fn(),
            };
        }),
    };
});

// Mock vis-data
vi.mock("vis-data", () => {
    class MockDataSet {
        constructor(data = []) {
            this._data = new Map(data.map((item) => [item.id, item]));
        }
        add(data) {
            const arr = Array.isArray(data) ? data : [data];
            arr.forEach((item) => this._data.set(item.id, item));
        }
        update(data) {
            const arr = Array.isArray(data) ? data : [data];
            arr.forEach((item) => this._data.set(item.id, item));
        }
        remove(ids) {
            const arr = Array.isArray(ids) ? ids : [ids];
            arr.forEach((id) => this._data.delete(id));
        }
        get(id) {
            if (id === undefined) return Array.from(this._data.values());
            return this._data.get(id) || null;
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

// Mock canvas for createIconImage
HTMLCanvasElement.prototype.getContext = vi.fn().mockReturnValue({
    createLinearGradient: vi.fn().mockReturnValue({
        addColorStop: vi.fn(),
    }),
    beginPath: vi.fn(),
    arc: vi.fn(),
    fill: vi.fn(),
    stroke: vi.fn(),
    drawImage: vi.fn(),
});

import NetworkVisualiser from "@/components/network-visualiser/NetworkVisualiser.vue";

describe("NetworkVisualiser.vue", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn().mockImplementation((url) => {
                if (url.includes("/api/v1/config")) {
                    return Promise.resolve({
                        data: { config: { display_name: "Test Node", identity_hash: "deadbeef" } },
                    });
                }
                if (url.includes("/api/v1/interface-stats")) {
                    return Promise.resolve({
                        data: {
                            interface_stats: {
                                interfaces: [{ name: "eth0", status: true, bitrate: 1000, txb: 100, rxb: 200 }],
                            },
                        },
                    });
                }
                if (url.includes("/api/v1/lxmf/conversations")) {
                    return Promise.resolve({ data: { conversations: [] } });
                }
                if (url.includes("/api/v1/path-table")) {
                    return Promise.resolve({
                        data: { path_table: [{ hash: "node1", interface: "eth0", hops: 1 }], total_count: 1 },
                    });
                }
                if (url.includes("/api/v1/announces")) {
                    return Promise.resolve({
                        data: {
                            announces: [
                                {
                                    destination_hash: "node1",
                                    aspect: "lxmf.delivery",
                                    display_name: "Remote Node",
                                    updated_at: new Date().toISOString(),
                                },
                            ],
                            total_count: 1,
                        },
                    });
                }
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn().mockImplementation((url) => {
                if (url.includes("/api/v1/path-table")) {
                    return Promise.resolve({
                        data: { path_table: [{ hash: "node1", interface: "eth0", hops: 1 }], total_count: 1 },
                    });
                }
                return Promise.resolve({ data: {} });
            }),
            isCancel: vi.fn().mockReturnValue(false),
        };
        window.api = axiosMock;

        // Mock URL.createObjectURL and URL.revokeObjectURL
        global.URL.createObjectURL = vi.fn().mockReturnValue("blob:mock-url");
        global.URL.revokeObjectURL = vi.fn();
    });

    afterEach(() => {
        delete window.api;
        vi.clearAllMocks();
    });

    const mountVisualiser = () => {
        return mount(NetworkVisualiser, {
            global: {
                mocks: {
                    $t: (msg) => {
                        const translations = {
                            "visualiser.reticulum_mesh": "Reticulum Mesh",
                            "visualiser.total_nodes": "Nodes",
                            "visualiser.total_edges": "Links",
                        };
                        return translations[msg] || msg;
                    },
                },
                stubs: {
                    Toggle: {
                        template:
                            '<input type="checkbox" :checked="modelValue" @change="$emit(\'update:modelValue\', $event.target.checked)" />',
                        props: ["modelValue"],
                    },
                },
            },
        });
    };

    it("renders the component and loads initial data", async () => {
        const wrapper = mountVisualiser();
        await wrapper.vm.$nextTick();

        // Wait for all async data loading to finish
        // We might need several nextTicks or a wait
        await new Promise((resolve) => setTimeout(resolve, 100));

        expect(wrapper.text()).toContain("Reticulum Mesh");
        expect(wrapper.text()).toContain("Nodes");
        expect(wrapper.text()).toContain("Links");
    });

    it("toggles control panel when the header strip is clicked", async () => {
        const wrapper = mountVisualiser();
        await new Promise((resolve) => setTimeout(resolve, 100));

        const before = wrapper.vm.isShowingControls;
        const headerRow = wrapper
            .findAll("div")
            .find((d) => d.text().includes("Reticulum Mesh") && d.classes().includes("cursor-pointer"));
        expect(headerRow).toBeDefined();
        await headerRow.trigger("click");
        expect(wrapper.vm.isShowingControls).toBe(!before);
    });

    it("shows loading overlay with batch indication during update", async () => {
        const wrapper = mountVisualiser();
        wrapper.vm.isLoading = true;
        wrapper.vm.totalNodesToLoad = 100;
        wrapper.vm.loadedNodesCount = 50;
        wrapper.vm.currentBatch = 2;
        wrapper.vm.totalBatches = 4;
        wrapper.vm.loadingStatus = "Processing Batch 2 / 4...";

        await wrapper.vm.$nextTick();

        const overlay = wrapper.find(".absolute.inset-0.z-20");
        expect(overlay.exists()).toBe(true);
        expect(overlay.text()).toContain("Batch 2 / 4");
        expect(overlay.text()).toContain("50%");
    });

    it("filters nodes based on search query", async () => {
        const wrapper = mountVisualiser();
        await new Promise((resolve) => setTimeout(resolve, 100));

        const searchInput = wrapper.find('input[type="text"]');
        await searchInput.setValue("Remote Node");

        // processVisualization is called via watcher on searchQuery
        await wrapper.vm.$nextTick();

        // The number of nodes in the DataSet should match the search
        // In our mock initial data, we have 'me', 'eth0', and 'node1' (Remote Node)
        // If we search for 'Remote Node', 'me' and 'eth0' might be filtered out depending on their labels
        expect(wrapper.vm.nodes.length).toBeGreaterThan(0);
    });

    it("fuzzing: handles large and messy network data without crashing", async () => {
        const wrapper = mountVisualiser();
        // Wait for initial load to finish
        await new Promise((resolve) => setTimeout(resolve, 200));

        // Generate messy path table
        const nodeCount = 500;
        const pathTable = Array.from({ length: nodeCount }, (_, i) => ({
            hash: `hash_${i}_${Math.random().toString(36).substring(7)}`,
            interface: i % 2 === 0 ? "eth0" : "wlan0",
            hops: Math.floor(Math.random() * 10),
        }));

        // Generate messy announces
        const announces = {};
        pathTable.forEach((entry, i) => {
            announces[entry.hash] = {
                destination_hash: entry.hash,
                aspect: i % 2 === 0 ? "lxmf.delivery" : "nomadnetwork.node",
                display_name: i % 5 === 0 ? null : `Node ${i} ${"!@#$%^&*()".charAt(i % 10)}`,
                custom_display_name: i % 7 === 0 ? "Custom Name" : undefined,
                updated_at: i % 10 === 0 ? "invalid-date" : new Date().toISOString(),
                identity_hash: `id_${i}`,
            };
        });

        wrapper.vm.pathTable = pathTable;
        wrapper.vm.announces = announces;

        // Trigger processVisualization
        // We set a smaller chunkSize in the test or just let it run
        // We can mock createIconImage to be faster
        wrapper.vm.createIconImage = vi.fn().mockResolvedValue("mock-icon");

        await wrapper.vm.processVisualization();

        expect(wrapper.vm.nodes.length).toBeGreaterThan(0);
        // Ensure no crash happened and cleanup worked
        expect(wrapper.vm.isLoading).toBe(false);
    });

    it("fuzzing: handles missing announce data gracefully", async () => {
        const wrapper = mountVisualiser();
        // Wait for initial load to finish
        await new Promise((resolve) => setTimeout(resolve, 200));

        // Set interfaces so eth0 exists
        wrapper.vm.interfaces = [{ name: "eth0", status: true }];

        // Path table with hashes that don't exist in announces
        wrapper.vm.pathTable = [
            { hash: "ghost1", interface: "eth0", hops: 1 },
            { hash: "ghost2", interface: "eth0", hops: 2 },
        ];
        wrapper.vm.announces = {}; // Empty announces

        await wrapper.vm.processVisualization();

        // Should only have 'me' and 'eth0' nodes
        expect(wrapper.vm.nodes.getIds()).toContain("me");
        expect(wrapper.vm.nodes.getIds()).toContain("eth0");
        expect(wrapper.vm.nodes.getIds()).not.toContain("ghost1");
    });

    it("fuzzing: handles circular or malformed links", async () => {
        const wrapper = mountVisualiser();
        // Wait for initial load to finish
        await new Promise((resolve) => setTimeout(resolve, 200));

        wrapper.vm.interfaces = [{ name: "eth0", status: true }];
        wrapper.vm.announces = {
            node1: {
                destination_hash: "node1",
                aspect: "lxmf.delivery",
                display_name: "Node 1",
                updated_at: new Date().toISOString(),
            },
        };

        // Malformed path table entries
        wrapper.vm.pathTable = [
            { hash: "node1", interface: "node1", hops: 1 }, // Circular link
            { hash: "node1", interface: null, hops: 1 }, // Missing interface
            { hash: null, interface: "eth0", hops: 1 }, // Missing hash
        ];

        await wrapper.vm.processVisualization();

        // Should still render 'me' and 'eth0'
        expect(wrapper.vm.nodes.getIds()).toContain("me");
        expect(wrapper.vm.nodes.getIds()).toContain("eth0");
    });

    it("performance: measures time to process 1000 nodes", async () => {
        const wrapper = mountVisualiser();
        // Wait for initial load to finish
        await new Promise((resolve) => setTimeout(resolve, 200));

        const nodeCount = 1000;

        const pathTable = Array.from({ length: nodeCount }, (_, i) => ({
            hash: `hash_${i}`,
            interface: "eth0",
            hops: 1,
        }));

        const announces = {};
        pathTable.forEach((entry, i) => {
            announces[entry.hash] = {
                destination_hash: entry.hash,
                aspect: "lxmf.delivery",
                display_name: `Node ${i}`,
                updated_at: new Date().toISOString(),
            };
        });

        wrapper.vm.pathTable = pathTable;
        wrapper.vm.announces = announces;
        wrapper.vm.createIconImage = vi.fn().mockResolvedValue("mock-icon");

        const start = performance.now();
        await wrapper.vm.processVisualization();
        const end = performance.now();

        console.log(`Processed ${nodeCount} nodes in visualizer in ${(end - start).toFixed(2)}ms`);
        expect(end - start).toBeLessThan(5000); // 5 seconds is generous for 1000 nodes with batching
    });

    it("memory: tracks icon cache growth", async () => {
        const wrapper = mountVisualiser();

        // Mock createIconImage to skip the Image loading part which times out in JSDOM
        const originalCreateIconImage = wrapper.vm.createIconImage;
        wrapper.vm.createIconImage = vi.fn().mockImplementation(async (iconName, fg, bg, size) => {
            const cacheKey = `${iconName}-${fg}-${bg}-${size}`;
            // Use blob: prefix so it gets cleared on unmount
            const mockBlobUrl = `blob:image/png/${iconName}`;
            wrapper.vm.iconCache[cacheKey] = mockBlobUrl;
            return mockBlobUrl;
        });

        const getMemory = () => process.memoryUsage().heapUsed / (1024 * 1024);
        const initialMem = getMemory();

        // Generate many unique icons to fill cache
        for (let i = 0; i < 1000; i++) {
            await wrapper.vm.createIconImage(`icon-${i}`, "#ff0000", "#000000", 64);
        }

        const afterIconMem = getMemory();
        expect(Object.keys(wrapper.vm.iconCache).length).toBe(1000);
        console.log(`Memory growth after 1000 unique icons in cache: ${(afterIconMem - initialMem).toFixed(2)}MB`);

        // Save reference to check if it's cleared after unmount
        const cacheRef = wrapper.vm.iconCache;
        wrapper.unmount();

        // After unmount, the cache should be empty or the reference should be cleared
        expect(Object.keys(cacheRef).length).toBe(0);
    });

    it("does not add offline interfaces when showDisabledInterfaces is false", async () => {
        vi.spyOn(NetworkVisualiser.methods, "init").mockImplementation(() => {});
        const wrapper = mountVisualiser();
        wrapper.vm.network = {
            getPositions: vi.fn().mockReturnValue({}),
            setOptions: vi.fn(),
            on: vi.fn(),
            destroy: vi.fn(),
        };
        wrapper.vm.config = { display_name: "Me", identity_hash: "abc" };
        wrapper.vm.interfaces = [
            { name: "eth_up", status: true, bitrate: 1000, txb: 0, rxb: 0 },
            { name: "eth_down", status: false, bitrate: 0, txb: 0, rxb: 0 },
        ];
        wrapper.vm.showDisabledInterfaces = false;
        await wrapper.vm.processVisualization();
        expect(wrapper.vm.nodes.getIds()).toContain("eth_up");
        expect(wrapper.vm.nodes.getIds()).not.toContain("eth_down");
    });

    it("keeps node positions from getPositions on subsequent layout passes", async () => {
        vi.spyOn(NetworkVisualiser.methods, "init").mockImplementation(() => {});
        const wrapper = mountVisualiser();
        const getPositions = vi
            .fn()
            .mockReturnValueOnce({})
            .mockReturnValue({
                me: { x: 0, y: 0 },
                eth0: { x: 301, y: 404 },
            });
        wrapper.vm.network = {
            getPositions,
            setOptions: vi.fn(),
            on: vi.fn(),
            destroy: vi.fn(),
        };
        wrapper.vm.config = { display_name: "Me", identity_hash: "abc" };
        wrapper.vm.interfaces = [{ name: "eth0", status: true, bitrate: 1000, txb: 0, rxb: 0 }];
        await wrapper.vm.processVisualization();
        await wrapper.vm.processVisualization();
        const n = wrapper.vm.nodes.get("eth0");
        expect(n.x).toBe(301);
        expect(n.y).toBe(404);
        expect(getPositions.mock.calls.length).toBeGreaterThanOrEqual(2);
    });
});
