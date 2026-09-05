// SPDX-License-Identifier: 0BSD

import { render, cleanup } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import NetworkVisualiser from "@/features/network-visualiser/components/NetworkVisualiser.svelte";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import en from "@/locales/en.json";

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
        registerTranslator(null);
        registerFallbackMessages(en);
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
            post: vi.fn().mockImplementation((url) => {
                if (url.includes("/api/v1/announces/query")) {
                    return Promise.resolve({ data: { announces: [], total_count: 0 } });
                }
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
        cleanup();
        delete window.api;
        vi.clearAllMocks();
    });

    it("renders properly without errors", () => {
        const { container } = render(NetworkVisualiser);
        expect(container).toBeTruthy();
    });
});
