import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import SieveFlowNetwork from "@/components/tools/internal/SieveFlowNetwork.vue";

vi.mock("vis-data", () => ({
    DataSet: vi.fn((items) => items),
}));

vi.mock("vis-network", () => ({
    Network: vi.fn(() => {
        throw new Error("graph init failed");
    }),
}));

describe("SieveFlowNetwork.vue", () => {
    it("does not throw when graph backend fails", async () => {
        const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
        const wrapper = mount(SieveFlowNetwork, {
            props: {
                filters: [{ id: "r1", enabled: true, terms: ["spam"], action: "hide" }],
                folders: [],
                labels: {},
            },
        });

        await wrapper.vm.$nextTick();
        await Promise.resolve();

        expect(wrapper.exists()).toBe(true);
        expect(warnSpy).toHaveBeenCalledWith("SieveFlowNetwork rebuild failed:", expect.any(Error));
        warnSpy.mockRestore();
    });
});
