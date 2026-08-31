// SPDX-License-Identifier: 0BSD

import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import MapDiscoverPanel from "@/components/map/internal/MapDiscoverPanel.vue";
import ToastUtils from "@/js/ToastUtils";

const HASH = "ab".repeat(16);

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
        loading: vi.fn(),
        dismiss: vi.fn(),
    },
}));

describe("MapDiscoverPanel", () => {
    beforeEach(() => {
        vi.useFakeTimers();
        vi.clearAllMocks();
        window.api = {
            get: vi.fn().mockResolvedValue({
                data: {
                    announces: [{ destination_hash: HASH, map_name: "Camp maps", map_count: 2 }],
                },
            }),
            post: vi.fn().mockResolvedValue({ data: { maps: [{ id: "a".repeat(16), name: "Camp", size: 12 }] } }),
        };
    });

    afterEach(() => {
        vi.useRealTimers();
        delete window.api;
    });

    it("loads heard map-data-v1 announces through window.api", async () => {
        const wrapper = mount(MapDiscoverPanel, {
            props: { listenEnabled: true },
            global: { mocks: { $t: (key) => key } },
        });
        await vi.advanceTimersByTimeAsync(250);
        await flushPromises();
        expect(window.api.get).toHaveBeenCalledWith("/api/v1/map/data/heard", {
            params: { search: undefined, limit: 250 },
        });
        expect(wrapper.text()).toContain("Camp maps");
        expect(wrapper.text()).toContain(HASH);
    });

    it("fetches a catalog over window.api.post", async () => {
        const wrapper = mount(MapDiscoverPanel, {
            props: { listenEnabled: true },
            global: { mocks: { $t: (key) => key } },
        });
        await vi.advanceTimersByTimeAsync(250);
        await flushPromises();
        await wrapper.find("button").trigger("click");
        await flushPromises();
        expect(window.api.post).toHaveBeenCalledWith("/api/v1/map/data/catalog", {
            destination_hash: HASH,
        });
        expect(wrapper.text()).toContain("Camp");
        expect(ToastUtils.loading).toHaveBeenCalled();
        expect(ToastUtils.success).toHaveBeenCalled();
    });

    it("shows empty catalog copy when the node lists no maps", async () => {
        window.api.post = vi.fn().mockResolvedValue({ data: { maps: [] } });
        const wrapper = mount(MapDiscoverPanel, {
            props: { listenEnabled: true },
            global: { mocks: { $t: (key) => key } },
        });
        await vi.advanceTimersByTimeAsync(250);
        await flushPromises();
        await wrapper.find("button").trigger("click");
        await flushPromises();
        expect(wrapper.text()).toContain("map.data_catalog_empty");
        expect(ToastUtils.info).toHaveBeenCalled();
    });

    it("does not fetch heard announces while listening is off", async () => {
        const wrapper = mount(MapDiscoverPanel, {
            props: { listenEnabled: false },
            global: { mocks: { $t: (key) => key } },
        });
        await vi.advanceTimersByTimeAsync(250);
        await flushPromises();
        expect(window.api.get).not.toHaveBeenCalled();
        expect(wrapper.text()).toContain("map.data_listen_off");
    });
});
