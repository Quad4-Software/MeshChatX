import { mount } from "@vue/test-utils";
import { describe, it, expect } from "vitest";
import RNodeCapabilitiesBanner from "@/components/rnode/RNodeCapabilitiesBanner.vue";
import RNodeDeviceSelector from "@/components/rnode/RNodeDeviceSelector.vue";
import RNodeFlashAction from "@/components/rnode/RNodeFlashAction.vue";
import RNodeAdvancedTools from "@/components/rnode/RNodeAdvancedTools.vue";
import RNodeDiagnosticsPanel from "@/components/rnode/RNodeDiagnosticsPanel.vue";
import { detectCapabilities } from "@/js/rnode/Capabilities.js";

const mountWith = (Component, props = {}) =>
    mount(Component, {
        props,
        global: {
            mocks: { $t: (k, params) => k + (params ? JSON.stringify(params) : "") },
            stubs: {
                MaterialDesignIcon: {
                    template: '<i class="mdi-stub" :data-icon-name="iconName"></i>',
                    props: ["iconName"],
                },
                "v-progress-circular": true,
                "v-progress-linear": true,
                "v-icon": true,
            },
        },
    });

describe("RNodeCapabilitiesBanner", () => {
    it("renders nothing when all transports are available", () => {
        const env = { isSecureContext: true, navigator: { userAgent: "x", serial: {}, bluetooth: {} } };
        const caps = detectCapabilities({ env });
        const wrapper = mountWith(RNodeCapabilitiesBanner, { capabilities: caps });
        expect(wrapper.html()).toBe("<!--v-if-->");
    });

    it("shows a serial warning with load polyfill action when polyfill missing", async () => {
        const env = { isSecureContext: true, navigator: { userAgent: "x", usb: {} } };
        const caps = detectCapabilities({ env });
        const wrapper = mountWith(RNodeCapabilitiesBanner, { capabilities: caps });
        expect(wrapper.text()).toContain("tools.rnode_flasher.support.serial.title");
        const button = wrapper.findAll("button").find((b) => b.text().includes("load_polyfill"));
        expect(button).toBeDefined();
        await button.trigger("click");
        expect(wrapper.emitted("action")[0]).toEqual(["load-polyfill"]);
    });

    it("shows bluetooth warning with android actions when bridge available", () => {
        const env = { isSecureContext: true, navigator: { userAgent: "Android" } };
        const caps = detectCapabilities({ env });
        const wrapper = mountWith(RNodeCapabilitiesBanner, {
            capabilities: caps,
            androidAvailable: true,
        });
        expect(wrapper.text()).toContain("tools.rnode_flasher.support.bluetooth.title");
        const labels = wrapper.findAll("button").map((b) => b.text());
        expect(labels.some((l) => l.includes("request_bluetooth"))).toBe(true);
    });
});

describe("RNodeDeviceSelector", () => {
    it("disables transports that are not available", () => {
        const caps = detectCapabilities({ env: { isSecureContext: true, navigator: { userAgent: "Android" } } });
        const wrapper = mountWith(RNodeDeviceSelector, {
            connectionMethod: "wifi",
            wifiHost: "192.168.1.50",
            selectedProduct: null,
            selectedModel: null,
            products: [{ id: 1, name: "Test", platform: 0x80, models: [{ id: 1, name: "M" }] }],
            capabilities: caps,
        });
        const serialBtn = wrapper.find('[data-testid="rnode-transport-serial"]');
        const wifiBtn = wrapper.find('[data-testid="rnode-transport-wifi"]');
        expect(serialBtn.attributes("disabled")).toBeDefined();
        expect(wifiBtn.attributes("disabled")).toBeUndefined();
    });

    it("shows DFU mode button only for nRF52 + serial", () => {
        const caps = detectCapabilities({ env: { isSecureContext: true, navigator: { userAgent: "x", serial: {} } } });
        const product = { id: 1, name: "P", platform: 0x70, models: [] };
        const wrapper = mountWith(RNodeDeviceSelector, {
            connectionMethod: "serial",
            wifiHost: "",
            selectedProduct: product,
            selectedModel: null,
            products: [product],
            capabilities: caps,
        });
        expect(wrapper.text()).toContain("tools.rnode_flasher.enter_dfu_mode");
    });
});

describe("RNodeFlashAction", () => {
    it("disables flash button when canFlash=false", () => {
        const wrapper = mountWith(RNodeFlashAction, { canFlash: false });
        const btn = wrapper.find('[data-testid="rnode-flash-btn"]');
        expect(btn.attributes("disabled")).toBeDefined();
    });
    it("renders error message when provided", () => {
        const wrapper = mountWith(RNodeFlashAction, { errorMessage: "boom" });
        expect(wrapper.text()).toContain("boom");
    });
    it("emits flash event when button clicked", async () => {
        const wrapper = mountWith(RNodeFlashAction, { canFlash: true });
        await wrapper.find('[data-testid="rnode-flash-btn"]').trigger("click");
        expect(wrapper.emitted("flash")).toBeTruthy();
    });
});

describe("RNodeAdvancedTools", () => {
    it("hides actions listed in disabledActions", () => {
        const wrapper = mountWith(RNodeAdvancedTools, {
            disabledActions: ["dump-eeprom", "wipe-eeprom"],
        });
        expect(wrapper.text()).not.toContain("tools.rnode_flasher.dump_eeprom");
        expect(wrapper.text()).not.toContain("tools.rnode_flasher.wipe_eeprom");
        expect(wrapper.text()).toContain("tools.rnode_flasher.detect_rnode");
    });
    it("emits action with action id", async () => {
        const wrapper = mountWith(RNodeAdvancedTools);
        const btn = wrapper.findAll("button").find((b) => b.text().includes("detect_rnode"));
        await btn.trigger("click");
        expect(wrapper.emitted("action")[0]).toEqual(["detect"]);
    });
});

describe("RNodeDiagnosticsPanel", () => {
    it("renders nothing when no diagnostics", () => {
        const wrapper = mountWith(RNodeDiagnosticsPanel, { diagnostics: null });
        expect(wrapper.html()).toBe("<!--v-if-->");
    });
    it("shows healthy badge when no issues", () => {
        const wrapper = mountWith(RNodeDiagnosticsPanel, {
            diagnostics: { issues: [], suggestionKeys: [], summary: { firmware_version: "1.80" } },
        });
        expect(wrapper.text()).toContain("tools.rnode_flasher.diagnostics.healthy");
    });
    it("shows issues list and needs_attention badge when issues exist", () => {
        const wrapper = mountWith(RNodeDiagnosticsPanel, {
            diagnostics: {
                issues: ["not_provisioned"],
                suggestionKeys: ["tools.rnode_flasher.diagnostics.suggestions.not_provisioned"],
                summary: { firmware_version: "1.80" },
            },
        });
        expect(wrapper.text()).toContain("tools.rnode_flasher.diagnostics.needs_attention");
        expect(wrapper.text()).toContain("tools.rnode_flasher.diagnostics.suggestions.not_provisioned");
    });
});
