import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import RNPathTracePage from "@/components/tools/RNPathTracePage.vue";

describe("RNPathTracePage.vue", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn(),
        };
        window.axios = axiosMock;
    });

    afterEach(() => {
        delete window.axios;
        vi.clearAllMocks();
    });

    const mountRNPathTracePage = (query = {}) => {
        return mount(RNPathTracePage, {
            global: {
                mocks: {
                    $t: (key) => key,
                    $route: { query },
                    $router: { push: vi.fn() },
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

    it("renders the path trace page", () => {
        const wrapper = mountRNPathTracePage();
        expect(wrapper.text()).toContain("tools.rnpath_trace.title");
    });

    it("validates destination hash", async () => {
        const wrapper = mountRNPathTracePage();
        const input = wrapper.find("input");
        const button = wrapper.find("button[title='Trace Path']");

        await input.setValue("invalid");
        expect(button.element.disabled).toBe(true);

        await input.setValue("a".repeat(32));
        expect(button.element.disabled).toBe(false);
    });

    it("calls trace API and displays results", async () => {
        axiosMock.get.mockResolvedValue({
            data: {
                hops: 2,
                interface: "UDP",
                next_hop: "next_hop_hash",
                path: [
                    { type: "local", name: "Local", hash: "local_hash" },
                    { type: "node", name: "Intermediate", hash: "node_hash", interface: "UDP" },
                    { type: "destination", name: "Destination", hash: "dest_hash" },
                ],
            },
        });

        const wrapper = mountRNPathTracePage();
        await wrapper.find("input").setValue("a".repeat(32));
        await wrapper.find("button[title='Trace Path']").trigger("click");

        await vi.waitFor(() => expect(wrapper.vm.isLoading).toBe(false));

        expect(axiosMock.get).toHaveBeenCalledWith(`/api/v1/rnpath/trace/${"a".repeat(32)}`);
        expect(wrapper.text()).toContain("2");
        expect(wrapper.text()).toContain("UDP");
        expect(wrapper.text()).toContain("Local");
        expect(wrapper.text()).toContain("Intermediate");
        expect(wrapper.text()).toContain("Destination");
    });

    it("handles trace error", async () => {
        axiosMock.get.mockRejectedValue({
            response: { data: { error: "Trace failed" } },
        });

        const wrapper = mountRNPathTracePage();
        await wrapper.find("input").setValue("a".repeat(32));
        await wrapper.find("button[title='Trace Path']").trigger("click");

        await vi.waitFor(() => expect(wrapper.vm.error).toBe("Trace failed"));
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("Trace Error");
        expect(wrapper.text()).toContain("Trace failed");
    });
});
