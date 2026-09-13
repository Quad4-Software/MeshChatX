// SPDX-License-Identifier: 0BSD

import { render, cleanup } from "@testing-library/svelte";
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
                getPositions: vi.fn().mockReturnValue({ me: { x: 0, y: 0 } }),
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

HTMLCanvasElement.prototype.getContext = vi.fn().mockReturnValue({
    createLinearGradient: vi.fn().mockReturnValue({
        addColorStop: vi.fn(),
    }),
    beginPath: vi.fn(),
    arc: vi.fn(),
    fill: vi.fn(),
    drawImage: vi.fn(),
    measureText: vi.fn().mockReturnValue({ width: 100 }),
    fillText: vi.fn(),
    stroke: vi.fn(),
    rect: vi.fn(),
    clearRect: vi.fn(),
    save: vi.fn(),
    restore: vi.fn(),
    scale: vi.fn(),
    translate: vi.fn(),
});
HTMLCanvasElement.prototype.toBlob = vi.fn().mockImplementation((cb) => {
    cb(new Blob(["mock-png"], { type: "image/png" }));
});

globalThis.__MESHCHATX_TEST_VISUALISER_WASM_BUNDLED__ = false;

import NetworkVisualiser from "@/features/network-visualiser/components/NetworkVisualiser.svelte";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import en from "@/locales/en.json";

describe("NetworkVisualiser.svelte", () => {
    let axiosMock;

    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages(en);
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
                if (url.includes("/api/v1/announces/query")) {
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
            isCancel: vi.fn().mockReturnValue(false),
        };
        window.api = axiosMock;

        global.URL.createObjectURL = vi.fn().mockReturnValue("blob:mock");
        global.URL.revokeObjectURL = vi.fn();
    });

    afterEach(() => {
        cleanup();
        delete window.api;
        vi.clearAllMocks();
    });

    it("mounts and renders correctly", async () => {
        const { container } = render(NetworkVisualiser);
        expect(container).toBeTruthy();
    });
});
