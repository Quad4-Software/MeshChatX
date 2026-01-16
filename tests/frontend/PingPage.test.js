import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import PingPage from "@/components/ping/PingPage.vue";
import DialogUtils from "@/js/DialogUtils";

vi.mock("@/js/DialogUtils", () => ({
    default: {
        alert: vi.fn(),
    },
}));

describe("PingPage.vue", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
        };
        window.axios = axiosMock;
    });

    afterEach(() => {
        delete window.axios;
        vi.clearAllMocks();
    });

    const mountPingPage = (query = {}) => {
        return mount(PingPage, {
            global: {
                mocks: {
                    $t: (key, params) => key + (params ? JSON.stringify(params) : ""),
                    $route: { query },
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

    it("renders the ping page", () => {
        const wrapper = mountPingPage();
        expect(wrapper.text()).toContain("ping.title");
    });

    it("shows alert for invalid hash when starting", async () => {
        const wrapper = mountPingPage();
        await wrapper.find("button").trigger("click");
        expect(DialogUtils.alert).toHaveBeenCalledWith("ping.invalid_hash");
    });

    it("pings and displays results", async () => {
        axiosMock.get.mockResolvedValue({
            data: {
                ping_result: {
                    rtt: 0.1234,
                    hops_there: 1,
                    hops_back: 1,
                    rssi: -50,
                    snr: 5,
                    quality: 100,
                    receiving_interface: "UDP",
                },
            },
        });

        const wrapper = mountPingPage();
        await wrapper.setData({ destinationHash: "a".repeat(32) });

        // Mock sleep to resolve immediately
        wrapper.vm.sleep = vi.fn().mockResolvedValue();

        // Start pinging, but make sure it stops
        const pingSpy = vi.spyOn(wrapper.vm, "ping");

        // We trigger start and then immediately set isRunning to false in the next microtask
        wrapper.vm.start();
        await vi.waitFor(() => expect(pingSpy).toHaveBeenCalled());
        wrapper.vm.isRunning = false;

        expect(wrapper.vm.pingResults.length).toBeGreaterThan(0);
        expect(wrapper.vm.pingResults[0]).toContain("duration=123.400ms");
        expect(wrapper.vm.pingResults[0]).toContain("rssi=-50dBm");
        expect(wrapper.text()).toContain("seq #1");
    });

    it("calls drop path API", async () => {
        axiosMock.post.mockResolvedValue({ data: { message: "Path dropped" } });
        const wrapper = mountPingPage();
        await wrapper.setData({ destinationHash: "a".repeat(32) });

        const dropButton = wrapper.findAll("button").find((b) => b.text().includes("ping.drop_path"));
        await dropButton.trigger("click");

        expect(axiosMock.post).toHaveBeenCalledWith(`/api/v1/destination/${"a".repeat(32)}/drop-path`);
        expect(DialogUtils.alert).toHaveBeenCalledWith("Path dropped");
    });
});
