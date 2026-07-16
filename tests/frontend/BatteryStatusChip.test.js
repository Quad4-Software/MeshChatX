// SPDX-License-Identifier: 0BSD

import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import BatteryStatusChip from "@/components/layout/BatteryStatusChip.vue";
import * as deviceBattery from "@/js/deviceBattery.js";

vi.mock("@/js/deviceBattery.js", async () => {
    const actual = await vi.importActual("@/js/deviceBattery.js");
    return {
        ...actual,
        getDeviceBatteryStatus: vi.fn(),
    };
});

describe("BatteryStatusChip.vue", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    const mountChip = () =>
        mount(BatteryStatusChip, {
            global: {
                mocks: {
                    $t: (key, params) => (params ? `${key}:${JSON.stringify(params)}` : key),
                    $router: { push: vi.fn() },
                },
                stubs: {
                    MaterialDesignIcon: true,
                },
            },
        });

    it("hides when battery status is unavailable", async () => {
        deviceBattery.getDeviceBatteryStatus.mockResolvedValue(null);
        const wrapper = mountChip();
        await flushPromises();
        expect(wrapper.find("button").exists()).toBe(false);
    });

    it("hides when probe throws", async () => {
        deviceBattery.getDeviceBatteryStatus.mockRejectedValue(new Error("boom"));
        const wrapper = mountChip();
        await flushPromises();
        expect(wrapper.find("button").exists()).toBe(false);
        expect(wrapper.vm.status).toBe(null);
    });

    it("renders level and navigates to about on click", async () => {
        deviceBattery.getDeviceBatteryStatus.mockResolvedValue({
            supported: true,
            level: 42,
            charging: false,
            source: "web",
        });
        const wrapper = mountChip();
        await flushPromises();
        const button = wrapper.find("button");
        expect(button.exists()).toBe(true);
        expect(button.text()).toContain("42%");
        await button.trigger("click");
        expect(wrapper.vm.$router.push).toHaveBeenCalledWith({ name: "about" });
    });

    it("hides after a later refresh loses battery support", async () => {
        deviceBattery.getDeviceBatteryStatus
            .mockResolvedValueOnce({
                supported: true,
                level: 20,
                charging: false,
                source: "electron",
            })
            .mockResolvedValueOnce(null);
        const wrapper = mountChip();
        await flushPromises();
        expect(wrapper.find("button").exists()).toBe(true);

        vi.advanceTimersByTime(60000);
        await flushPromises();
        expect(wrapper.find("button").exists()).toBe(false);
    });

    it("shows low-battery styling under 15 percent", async () => {
        deviceBattery.getDeviceBatteryStatus.mockResolvedValue({
            supported: true,
            level: 8,
            charging: false,
            source: "android",
        });
        const wrapper = mountChip();
        await flushPromises();
        expect(wrapper.find("button").classes().join(" ")).toContain("text-red-700");
    });
});
