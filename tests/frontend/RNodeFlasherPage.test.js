import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import RNodeFlasherPage from "@/components/tools/RNodeFlasherPage.vue";

describe("RNodeFlasherPage.vue", () => {
    beforeEach(() => {
        // Mock global fetch for the latest_release proxy
        window.fetch = vi.fn().mockImplementation((url) => {
            if (typeof url === "string" && url.includes("/api/v1/tools/rnode/latest_release")) {
                return Promise.resolve({
                    ok: true,
                    json: () =>
                        Promise.resolve({
                            tag_name: "v1.0",
                            assets: [{ name: "firmware.zip", browser_download_url: "http://example.com/firmware.zip" }],
                        }),
                });
            }
            return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
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

        const advancedButton = wrapper.findAll("button").find((b) => b.text().includes("tools.rnode_flasher.advanced"));
        await advancedButton.trigger("click");

        expect(wrapper.vm.showAdvanced).toBe(true);
        expect(wrapper.text()).toContain("tools.rnode_flasher.advanced_tools");
    });

    it("switches connection method", async () => {
        const wrapper = mountRNodeFlasherPage();

        const wifiButton = wrapper.findAll('[data-testid="rnode-transport-wifi"]')[0];
        await wifiButton.trigger("click");

        expect(wrapper.vm.connectionMethod).toBe("wifi");
        expect(wrapper.find("input[type='text']").exists()).toBe(true);
    });

    it("loads products from products.js", () => {
        const wrapper = mountRNodeFlasherPage();
        expect(wrapper.vm.products.length).toBeGreaterThan(0);
        const options = wrapper.findAll("select:first-of-type option");
        expect(options.length).toBeGreaterThan(1);
    });

    it("resolves recommended asset url from the release when present", () => {
        const wrapper = mountRNodeFlasherPage();
        wrapper.vm.selectedProduct = { firmware_filename: "firmware.zip" };
        wrapper.vm.latestRelease = {
            assets: [{ name: "firmware.zip", browser_download_url: "https://gitea/example.zip" }],
        };
        expect(wrapper.vm._resolveRecommendedAssetUrl()).toBe("https://gitea/example.zip");
    });

    it("falls back to the gitea releases/latest/download URL when the release lookup failed", () => {
        const wrapper = mountRNodeFlasherPage();
        wrapper.vm.selectedProduct = { firmware_filename: "rnode_firmware_heltec32v3.zip" };
        wrapper.vm.latestRelease = null;
        const url = wrapper.vm._resolveRecommendedAssetUrl();
        expect(url).toMatch(/\/Reticulum\/RNode_Firmware\/releases\/latest\/download\/rnode_firmware_heltec32v3\.zip$/);
    });
});
