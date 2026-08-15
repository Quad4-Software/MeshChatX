// SPDX-License-Identifier: 0BSD

import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import MapPublishPanel from "@/components/map/internal/MapPublishPanel.vue";
import ToastUtils from "@/js/ToastUtils";

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

describe("MapPublishPanel", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        window.api = {
            get: vi.fn().mockImplementation((url) => {
                if (url.includes("/status")) {
                    return Promise.resolve({
                        data: {
                            display_name: "Maps",
                            announce_enabled: false,
                            announce_interval: 900,
                            published_count: 0,
                        },
                    });
                }
                return Promise.resolve({ data: { maps: [] } });
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
            patch: vi.fn().mockResolvedValue({ data: {} }),
            delete: vi.fn().mockResolvedValue({ data: {} }),
        };
    });

    afterEach(() => {
        delete window.api;
    });

    it("keeps announce controls off until a map is published", async () => {
        const wrapper = mount(MapPublishPanel, {
            global: { mocks: { $t: (key) => key } },
        });
        await flushPromises();
        const checkbox = wrapper.find('input[type="checkbox"]');
        expect(checkbox.element.checked).toBe(false);
        expect(checkbox.element.disabled).toBe(true);
        expect(wrapper.text()).toContain("map.data_announce_needs_publish");
        const announceNow = wrapper.findAll("button").find((btn) => btn.text() === "map.data_announce_now");
        expect(announceNow.attributes("disabled")).toBeDefined();
    });

    it("enables announce after a published map is listed", async () => {
        window.api.get = vi.fn().mockImplementation((url) => {
            if (url.includes("/status")) {
                return Promise.resolve({
                    data: {
                        display_name: "Maps",
                        announce_enabled: false,
                        announce_interval: 900,
                        published_count: 1,
                    },
                });
            }
            return Promise.resolve({
                data: { maps: [{ map_id: "a".repeat(16), name: "Camp", format: "geojson", size: 12 }] },
            });
        });
        const wrapper = mount(MapPublishPanel, {
            global: { mocks: { $t: (key) => key } },
        });
        await flushPromises();
        const checkbox = wrapper.find('input[type="checkbox"]');
        expect(checkbox.element.disabled).toBe(false);
        const announceNow = wrapper.findAll("button").find((btn) => btn.text() === "map.data_announce_now");
        expect(announceNow.attributes("disabled")).toBeUndefined();
    });
});
