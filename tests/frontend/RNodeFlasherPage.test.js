import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

const { toastError, toastSuccess, toastInfo, toastWarning } = vi.hoisted(() => ({
    toastError: vi.fn(),
    toastSuccess: vi.fn(),
    toastInfo: vi.fn(),
    toastWarning: vi.fn(),
}));

vi.mock("@/js/ToastUtils.js", () => ({
    default: {
        error: toastError,
        success: toastSuccess,
        info: toastInfo,
        warning: toastWarning,
    },
}));

import RNodeFlasherPage from "@/components/tools/RNodeFlasherPage.vue";

describe("RNodeFlasherPage.vue", () => {
    beforeEach(() => {
        toastError.mockClear();
        toastSuccess.mockClear();
        toastInfo.mockClear();
        toastWarning.mockClear();

        window.fetch = vi.fn().mockImplementation((url) => {
            if (typeof url === "string" && url.includes("/api/v1/tools/rnode/latest_release")) {
                return Promise.resolve({
                    ok: true,
                    json: () =>
                        Promise.resolve({
                            tag_name: "v1.0",
                            assets: [
                                {
                                    name: "firmware.zip",
                                    browser_download_url:
                                        "https://github.com/markqvist/RNode_Firmware/releases/download/v1/firmware.zip",
                                },
                            ],
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

    it("requests latest_release without a repo query (GitHub default on server)", async () => {
        mountRNodeFlasherPage();
        await vi.waitFor(() => {
            expect(window.fetch).toHaveBeenCalled();
        });
        const releaseCalls = window.fetch.mock.calls.filter(
            (c) => typeof c[0] === "string" && c[0].includes("latest_release")
        );
        expect(releaseCalls.length).toBeGreaterThanOrEqual(1);
        const u = releaseCalls[0][0];
        expect(u).toBe("/api/v1/tools/rnode/latest_release");
        expect(u).not.toContain("?");
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

    it("falls back to the GitHub releases/latest/download URL when the release lookup failed", () => {
        const wrapper = mountRNodeFlasherPage();
        wrapper.vm.selectedProduct = { firmware_filename: "rnode_firmware_heltec32v3.zip" };
        wrapper.vm.latestRelease = null;
        const url = wrapper.vm._resolveRecommendedAssetUrl();
        expect(url).toBe(
            "https://github.com/markqvist/RNode_Firmware/releases/latest/download/rnode_firmware_heltec32v3.zip"
        );
    });

    it("uses model firmware_filename when present for fallback URL", () => {
        const wrapper = mountRNodeFlasherPage();
        wrapper.vm.selectedProduct = { models: [] };
        wrapper.vm.selectedModel = { firmware_filename: "rnode_firmware_tbeam.zip" };
        wrapper.vm.latestRelease = null;
        expect(wrapper.vm._resolveRecommendedAssetUrl()).toBe(
            "https://github.com/markqvist/RNode_Firmware/releases/latest/download/rnode_firmware_tbeam.zip"
        );
    });

    it("links footer firmware and flasher pages to GitHub", () => {
        const wrapper = mountRNodeFlasherPage();
        const html = wrapper.html();
        expect(html).toContain('href="https://github.com/markqvist/RNode_Firmware"');
        expect(html).toContain('href="https://github.com/liamcottle/rnode-flasher"');
    });

    it("downloadRecommendedFirmware requests proxied download with encoded GitHub URL", async () => {
        const zipBytes = new Uint8Array([0x50, 0x4b, 0x03, 0x04, 0x00]);
        const assetUrl = "https://github.com/markqvist/RNode_Firmware/releases/download/v1.0/firmware.zip";

        window.fetch = vi.fn().mockImplementation((url) => {
            if (typeof url === "string" && url.includes("/api/v1/tools/rnode/latest_release")) {
                return Promise.resolve({
                    ok: true,
                    json: () =>
                        Promise.resolve({
                            tag_name: "v1.0",
                            assets: [{ name: "firmware.zip", browser_download_url: assetUrl }],
                        }),
                });
            }
            if (typeof url === "string" && url.includes("/api/v1/tools/rnode/download_firmware")) {
                expect(url).toContain(encodeURIComponent(assetUrl));
                return Promise.resolve({
                    ok: true,
                    blob: () => Promise.resolve(new Blob([zipBytes], { type: "application/zip" })),
                });
            }
            return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
        });

        const wrapper = mount(RNodeFlasherPage, {
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
                    RNodeFirmwareSelector: {
                        name: "RNodeFirmwareSelectorStub",
                        template: "<div />",
                        methods: { setFile: vi.fn() },
                    },
                },
            },
        });
        await vi.waitFor(() => expect(wrapper.vm.latestRelease).not.toBeNull());
        wrapper.vm.selectedProduct = { firmware_filename: "firmware.zip" };

        await wrapper.vm.downloadRecommendedFirmware();
        await flushPromises();

        expect(toastSuccess).toHaveBeenCalledWith("tools.rnode_flasher.alerts.firmware_downloaded");
        expect(wrapper.vm.firmwareFile).not.toBe(null);
        expect(wrapper.vm.firmwareFile.name).toBe("firmware.zip");
    });

    it("downloadRecommendedFirmware shows error when no firmware filename", async () => {
        const wrapper = mountRNodeFlasherPage();
        wrapper.vm.selectedProduct = null;
        wrapper.vm.selectedModel = null;
        await wrapper.vm.downloadRecommendedFirmware();
        expect(toastError).toHaveBeenCalledWith("tools.rnode_flasher.errors.firmware_not_found_in_release");
    });

    it("downloadRecommendedFirmware shows error when download fails", async () => {
        window.fetch = vi.fn().mockImplementation((url) => {
            if (typeof url === "string" && url.includes("/api/v1/tools/rnode/latest_release")) {
                return Promise.resolve({
                    ok: true,
                    json: () =>
                        Promise.resolve({
                            tag_name: "v1.0",
                            assets: [
                                {
                                    name: "firmware.zip",
                                    browser_download_url:
                                        "https://github.com/markqvist/RNode_Firmware/releases/download/v1/firmware.zip",
                                },
                            ],
                        }),
                });
            }
            if (typeof url === "string" && url.includes("/api/v1/tools/rnode/download_firmware")) {
                return Promise.resolve({
                    ok: false,
                    status: 502,
                    statusText: "Bad Gateway",
                    json: () => Promise.resolve({ error: "upstream broke" }),
                });
            }
            return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
        });

        const wrapper = mountRNodeFlasherPage();
        await vi.waitFor(() => expect(wrapper.vm.latestRelease).not.toBeNull());
        wrapper.vm.selectedProduct = { firmware_filename: "firmware.zip" };

        await wrapper.vm.downloadRecommendedFirmware();

        expect(toastError).toHaveBeenCalled();
        const msg = toastError.mock.calls[0][0];
        expect(msg).toContain("tools.rnode_flasher.errors.failed_download");
        expect(msg).toContain("upstream broke");
    });
});
