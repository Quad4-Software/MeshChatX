import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import RNProbePage from "@/components/rnprobe/RNProbePage.vue";
import DialogUtils from "@/js/DialogUtils";

vi.mock("@/js/DialogUtils", () => ({
    default: {
        alert: vi.fn(),
    },
}));

describe("RNProbePage.vue", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            post: vi.fn(),
        };
        window.axios = axiosMock;
    });

    afterEach(() => {
        delete window.axios;
        vi.clearAllMocks();
    });

    const mountRNProbePage = () => {
        return mount(RNProbePage, {
            global: {
                mocks: {
                    $t: (key, params) => key + (params ? JSON.stringify(params) : ""),
                },
                stubs: {
                    MaterialDesignIcon: {
                        template: '<div class="mdi-stub" :data-icon-name="iconName"></div>',
                        props: ["iconName"],
                    },
                },
            },
        });
    };

    it("renders the rnprobe page", () => {
        const wrapper = mountRNProbePage();
        expect(wrapper.text()).toContain("rnprobe.title");
    });

    it("calls probe API and displays results", async () => {
        axiosMock.post.mockResolvedValue({
            data: {
                sent: 1,
                delivered: 1,
                timeouts: 0,
                failed: 0,
                results: [
                    {
                        probe_number: 1,
                        size: 16,
                        destination: "dest",
                        status: "delivered",
                        hops: 1,
                        rtt_string: "123ms",
                        reception_stats: { rssi: -50, snr: 5, quality: 100 },
                    },
                ],
            },
        });

        const wrapper = mountRNProbePage();
        await wrapper.setData({ destinationHash: "a".repeat(32) });

        await wrapper.find("button[class*='primary-chip']").trigger("click");

        await vi.waitFor(() => expect(wrapper.vm.isRunning).toBe(false));

        expect(axiosMock.post).toHaveBeenCalled();
        expect(wrapper.text()).toContain("rnprobe.summary");
        expect(wrapper.text()).toContain("rnprobe.delivered");
        expect(wrapper.text()).toContain("123ms");
    });

    it("handles probe errors", async () => {
        axiosMock.post.mockRejectedValue({
            response: { data: { message: "Probe failed" } },
        });

        const wrapper = mountRNProbePage();
        await wrapper.setData({ destinationHash: "a".repeat(32) });

        await wrapper.find("button[class*='primary-chip']").trigger("click");

        await vi.waitFor(() => expect(wrapper.vm.isRunning).toBe(false));
        expect(DialogUtils.alert).toHaveBeenCalledWith("Probe failed");
    });
});
