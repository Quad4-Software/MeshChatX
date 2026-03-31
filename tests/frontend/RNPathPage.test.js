import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import RNPathPage from "@/components/tools/RNPathPage.vue";

describe("RNPathPage.vue", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
        };
        window.api = axiosMock;

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/rnpath/table") {
                return Promise.resolve({
                    data: {
                        table: [
                            {
                                hash: "a".repeat(32),
                                hops: 1,
                                via: "b".repeat(32),
                                interface: "UDP",
                                expires: 1234567890,
                            },
                        ],
                    },
                });
            }
            if (url === "/api/v1/rnpath/rates") {
                return Promise.resolve({
                    data: {
                        rates: [
                            {
                                hash: "c".repeat(32),
                                last: 1234567890,
                                timestamps: [],
                                rate_violations: 0,
                                blocked_until: 0,
                            },
                        ],
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });
    });

    afterEach(() => {
        delete window.api;
    });

    const mountRNPathPage = () => {
        return mount(RNPathPage, {
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

    it("renders and loads data", async () => {
        const wrapper = mountRNPathPage();
        await vi.waitFor(() => expect(wrapper.vm.isLoading).toBe(false));

        expect(wrapper.text()).toContain("RNPath");
        expect(wrapper.vm.pathTable.length).toBe(1);
        expect(wrapper.vm.rateTable.length).toBe(1);
    });

    it("switches tabs", async () => {
        const wrapper = mountRNPathPage();
        await vi.waitFor(() => expect(wrapper.vm.isLoading).toBe(false));

        const ratesButton = wrapper.findAll("button").find((b) => b.text() === "Rates");
        await ratesButton.trigger("click");
        expect(wrapper.vm.tab).toBe("rates");

        const actionsButton = wrapper.findAll("button").find((b) => b.text() === "Actions");
        await actionsButton.trigger("click");
        expect(wrapper.vm.tab).toBe("actions");
    });

    it("calls request path API", async () => {
        const wrapper = mountRNPathPage();
        await vi.waitFor(() => expect(wrapper.vm.isLoading).toBe(false));

        await wrapper.setData({ tab: "actions", requestHash: "d".repeat(32) });

        const requestButton = wrapper.findAll("button").find((b) => b.text() === "Request");
        await requestButton.trigger("click");

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/rnpath/request", {
            destination_hash: "d".repeat(32),
        });
    });
});
