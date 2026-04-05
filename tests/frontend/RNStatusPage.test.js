import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import RNStatusPage from "@/components/rnstatus/RNStatusPage.vue";

describe("RNStatusPage.vue", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn(),
        };
        window.api = axiosMock;

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/rnstatus") {
                return Promise.resolve({
                    data: {
                        interfaces: [
                            {
                                name: "Interface 1",
                                status: "Up",
                                discovered: true,
                                bitrate: "100 bps",
                                rx_bytes_str: "10 B",
                                tx_bytes_str: "5 B",
                            },
                        ],
                        link_count: 5,
                        blackhole_enabled: true,
                        blackhole_count: 10,
                        blackhole_sources: ["src1"],
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });
    });

    afterEach(() => {
        delete window.api;
        vi.clearAllMocks();
    });

    const mountRNStatusPage = () => {
        return mount(RNStatusPage, {
            global: {
                mocks: {
                    $t: (key) => key,
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

    it("renders and loads status data", async () => {
        const wrapper = mountRNStatusPage();
        await vi.waitFor(() => expect(wrapper.vm.isLoading).toBe(false));

        expect(wrapper.text()).toContain("RNStatus - Network Status");
        expect(wrapper.text()).toContain("Interface 1");
        expect(wrapper.text()).toContain("Discovered");
        expect(wrapper.text()).toContain("Active Links: 5");
        expect(wrapper.text()).toContain("Blackhole: Publishing");
        expect(wrapper.text()).toContain("src1");
    });

    it("refreshes status when button is clicked", async () => {
        const wrapper = mountRNStatusPage();
        await vi.waitFor(() => expect(wrapper.vm.isLoading).toBe(false));

        const refreshButton = wrapper.find("button");
        await refreshButton.trigger("click");

        expect(axiosMock.get).toHaveBeenCalled();
    });

    it("toggles link stats", async () => {
        const wrapper = mountRNStatusPage();
        await vi.waitFor(() => expect(wrapper.vm.isLoading).toBe(false));

        const checkbox = wrapper.find("input[type='checkbox']");
        await checkbox.setValue(true);

        expect(axiosMock.get).toHaveBeenCalledWith(
            "/api/v1/rnstatus",
            expect.objectContaining({
                params: expect.objectContaining({ include_link_stats: true }),
            })
        );
    });
});
