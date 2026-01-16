import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import RNodeFlasherPage from "@/components/tools/RNodeFlasherPage.vue";

describe("RNodeFlasherPage.vue", () => {
    beforeEach(() => {
        // Mock global fetch for release fetching
        window.fetch = vi.fn().mockResolvedValue({
            ok: true,
            json: () =>
                Promise.resolve({
                    assets: [{ name: "firmware.zip", browser_download_url: "http://example.com/firmware.zip" }],
                }),
        });
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    const mountRNodeFlasherPage = () => {
        return mount(RNodeFlasherPage, {
            global: {
                mocks: {
                    $t: (key, params) => key + (params ? JSON.stringify(params) : ""),
                    $router: { push: vi.fn() },
                },
                stubs: {
                    MaterialDesignIcon: {
                        template: '<div class="mdi-stub" :data-icon-name="iconName"></div>',
                        props: ["iconName"],
                    },
                    "v-icon": true,
                    "v-progress-circular": true,
                    "v-progress-linear": true,
                },
            },
        });
    };

    it("renders the flasher page", () => {
        const wrapper = mountRNodeFlasherPage();
        expect(wrapper.text()).toContain("tools.rnode_flasher.title");
        expect(wrapper.text()).toContain("1. tools.rnode_flasher.select_device");
    });

    it("toggles advanced mode", async () => {
        const wrapper = mountRNodeFlasherPage();
        expect(wrapper.vm.showAdvanced).toBe(false);

        const advancedButton = wrapper.findAll("button").find((b) => b.text().includes("Advanced"));
        await advancedButton.trigger("click");

        expect(wrapper.vm.showAdvanced).toBe(true);
        expect(wrapper.text()).toContain("tools.rnode_flasher.advanced_tools");
    });

    it("switches connection method", async () => {
        const wrapper = mountRNodeFlasherPage();

        const wifiButton = wrapper.findAll("button").find((b) => b.text().includes("tools.rnode_flasher.wifi"));
        await wifiButton.trigger("click");

        expect(wrapper.vm.connectionMethod).toBe("wifi");
        expect(wrapper.find("input[type='text']").exists()).toBe(true); // IP input
    });

    it("loads products from products.js", () => {
        const wrapper = mountRNodeFlasherPage();
        expect(wrapper.vm.products.length).toBeGreaterThan(0);
        const options = wrapper.findAll("select:first-of-type option");
        expect(options.length).toBeGreaterThan(1);
    });
});
