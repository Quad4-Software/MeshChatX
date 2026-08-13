// SPDX-License-Identifier: 0BSD

import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import MapDiscoverPanel from "@/components/map/internal/MapDiscoverPanel.vue";

const HASH = "ab".repeat(16);

describe("MapDiscoverPanel", () => {
    beforeEach(() => {
        vi.useFakeTimers();
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
    });
});
