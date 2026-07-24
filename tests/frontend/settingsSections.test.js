// SPDX-License-Identifier: 0BSD

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import SettingToggleRow from "../../meshchatx/src/frontend/components/settings/SettingToggleRow.vue";
import StrangerProtectionSettingsSection from "../../meshchatx/src/frontend/components/settings/sections/StrangerProtectionSettingsSection.vue";
import BanishmentSettingsSection from "../../meshchatx/src/frontend/components/settings/sections/BanishmentSettingsSection.vue";
import TelephonySettingsSection from "../../meshchatx/src/frontend/components/settings/sections/TelephonySettingsSection.vue";
import AppearanceSettingsSection from "../../meshchatx/src/frontend/components/settings/sections/AppearanceSettingsSection.vue";
import BatterySettingsSection from "../../meshchatx/src/frontend/components/settings/sections/BatterySettingsSection.vue";
import VisualiserSettingsSection from "../../meshchatx/src/frontend/components/settings/sections/VisualiserSettingsSection.vue";
import BlockedSettingsSection from "../../meshchatx/src/frontend/components/settings/sections/BlockedSettingsSection.vue";
import AndroidSettingsSection from "../../meshchatx/src/frontend/components/settings/sections/AndroidSettingsSection.vue";
import ArchiverSettingsSection from "../../meshchatx/src/frontend/components/settings/sections/ArchiverSettingsSection.vue";

describe("SettingToggleRow", () => {
    it("renders title and description and emits updates", async () => {
        const wrapper = mount(SettingToggleRow, {
            props: {
                id: "probe-toggle",
                modelValue: false,
                title: "Probe title",
                description: "Probe description",
                hint: "Probe hint",
            },
        });
        expect(wrapper.text()).toContain("Probe title");
        expect(wrapper.text()).toContain("Probe description");
        expect(wrapper.text()).toContain("Probe hint");
        await wrapper.findComponent({ name: "Toggle" }).vm.$emit("update:modelValue", true);
        expect(wrapper.emitted("update:modelValue")).toEqual([[true]]);
    });
});

describe("StrangerProtectionSettingsSection", () => {
    it("emits dedicated events for each stranger toggle", async () => {
        const wrapper = mount(StrangerProtectionSettingsSection, {
            props: {
                visible: true,
                config: {
                    block_attachments_from_strangers: false,
                    block_all_from_strangers: false,
                    show_unknown_contact_banner: true,
                    warn_on_stranger_links: true,
                },
            },
            global: {
                mocks: { $t: (key) => key },
            },
        });
        const rows = wrapper.findAllComponents({ name: "SettingToggleRow" });
        expect(rows).toHaveLength(4);
        await rows[0].vm.$emit("update:modelValue", true);
        await rows[1].vm.$emit("update:modelValue", true);
        await rows[2].vm.$emit("update:modelValue", false);
        await rows[3].vm.$emit("update:modelValue", false);
        expect(wrapper.emitted("block-attachments-change")).toEqual([[true]]);
        expect(wrapper.emitted("block-all-change")).toEqual([[true]]);
        expect(wrapper.emitted("unknown-banner-change")).toEqual([[false]]);
        expect(wrapper.emitted("warn-links-change")).toEqual([[false]]);
    });
});

describe("BanishmentSettingsSection", () => {
    it("shows text and color controls only when enabled", async () => {
        const wrapper = mount(BanishmentSettingsSection, {
            props: {
                visible: true,
                config: {
                    banished_effect_enabled: false,
                    banished_text: "gone",
                    banished_color: "#112233",
                },
            },
            global: {
                mocks: { $t: (key) => key },
            },
        });
        expect(wrapper.find("input[type='text']").exists()).toBe(false);
        await wrapper.setProps({
            config: {
                banished_effect_enabled: true,
                banished_text: "gone",
                banished_color: "#112233",
            },
        });
        expect(wrapper.find("input[type='text']").exists()).toBe(true);
        await wrapper.find("input[type='text']").setValue("banished");
        expect(wrapper.emitted("text-change")?.[0]).toEqual(["banished"]);
    });
});

describe("TelephonySettingsSection", () => {
    it("emits enabled-change from the telephone toggle", async () => {
        const wrapper = mount(TelephonySettingsSection, {
            props: {
                visible: true,
                config: { telephone_enabled: true },
            },
        });
        await wrapper.findComponent({ name: "SettingToggleRow" }).vm.$emit("update:modelValue", false);
        expect(wrapper.emitted("enabled-change")).toEqual([[false]]);
    });
});

describe("AppearanceSettingsSection", () => {
    it("emits theme and field events without mutating config prop", async () => {
        const config = {
            theme: "light",
            messages_sidebar_position: "left",
            message_font_size: 14,
            message_icon_size: 28,
            ui_transparency: 0,
            ui_glass_enabled: true,
            messages_multi_pane_enabled: false,
            nomad_tabs_enabled: false,
            rrc_enabled: false,
            rrc_unread_badges_enabled: true,
            message_outbound_bubble_color: "#4f46e5",
            message_inbound_bubble_color: null,
            message_failed_bubble_color: "#ef4444",
            message_waiting_bubble_color: "#e5e7eb",
        };
        const wrapper = mount(AppearanceSettingsSection, {
            props: {
                visible: true,
                config,
                detailedOutboundSendStatus: false,
                outboundTransferProgressEnabled: false,
                messageTimestampGroupingEnabled: false,
                messageIconPreviewStyle: { width: "28px", height: "28px" },
            },
            global: {
                mocks: { $t: (key) => key },
            },
        });
        expect(wrapper.text()).toContain("app.appearance");
        const themeSelect = wrapper.find("select");
        await themeSelect.setValue("dark");
        expect(wrapper.emitted("update-field")?.at(-1)).toEqual([{ key: "theme", value: "dark" }]);
        expect(wrapper.emitted("theme-change")).toHaveLength(1);
        expect(config.theme).toBe("light");
        await wrapper.findComponent({ name: "Toggle" }).vm.$emit("update:modelValue", false);
        expect(wrapper.emitted("update-field")?.at(-1)).toEqual([{ key: "ui_glass_enabled", value: false }]);
        expect(wrapper.emitted("ui-glass-enabled-change")).toHaveLength(1);
    });
});

describe("BatterySettingsSection", () => {
    it("emits patch and apply events for battery controls", async () => {
        const batterySaver = {
            enabled: false,
            disableVisualiserDiscovery: false,
            hideOfflineInterfaces: false,
            maxVisualiserInterfaces: 0,
            visualiserReloadSeconds: 0,
            disableVisualiserLiveLayout: false,
            reduceBackgroundPolling: false,
            backgroundPollMultiplier: 2,
            reduceInterfacesDiscovery: false,
            interfacesStatsPollSeconds: 5,
            interfacesDiscoveryPollSeconds: 30,
            applyInterfaceBitrateLimits: false,
            interfaceBitrateLimits: {},
        };
        const wrapper = mount(BatterySettingsSection, {
            props: {
                visible: true,
                batterySaver,
                batteryInterfaceRows: [],
                batteryBitrateBusy: false,
            },
            global: {
                mocks: { $t: (key) => key },
            },
        });
        expect(wrapper.text()).toContain("settings.battery.title");
        const toggles = wrapper.findAllComponents({ name: "Toggle" });
        expect(toggles.length).toBeGreaterThan(0);
        await toggles[0].vm.$emit("update:modelValue", true);
        expect(wrapper.emitted("enabled-change")).toEqual([[true]]);
    });
});

describe("VisualiserSettingsSection", () => {
    it("emits renderer and visibility changes", async () => {
        const wrapper = mount(VisualiserSettingsSection, {
            props: {
                visible: true,
                renderer: "auto",
                showDisabledInterfaces: false,
                showDiscoveredInterfaces: true,
            },
            global: {
                mocks: { $t: (key) => key },
            },
        });
        expect(wrapper.text()).toContain("visualiser.title");
        await wrapper.find("select").setValue("webgl");
        expect(wrapper.emitted("renderer-change")?.at(-1)).toEqual(["webgl"]);
        const toggles = wrapper.findAllComponents({ name: "Toggle" });
        await toggles[0].vm.$emit("update:modelValue", true);
        expect(wrapper.emitted("show-disabled-change")).toEqual([[true]]);
    });
});

describe("BlockedSettingsSection", () => {
    it("renders banished management link", () => {
        const wrapper = mount(BlockedSettingsSection, {
            props: { visible: true },
            global: {
                stubs: {
                    RouterLink: {
                        props: ["to"],
                        template: '<a :href="to.name"><slot /></a>',
                    },
                },
            },
        });
        expect(wrapper.text()).toContain("Banished");
        expect(wrapper.text()).toContain("Manage Banished");
    });
});

describe("AndroidSettingsSection", () => {
    it("emits privacy updates, remote backend actions, and share-apk", async () => {
        const wrapper = mount(AndroidSettingsSection, {
            props: {
                visible: true,
                androidShellPrivacy: {
                    blockScreenshots: false,
                    clearClipboardOnBackground: false,
                },
                remoteBackendUrl: "",
                effectiveBackendUrl: "https://127.0.0.1:8000",
                remoteBackendActive: false,
            },
            global: {
                mocks: { $t: (key) => key },
            },
        });
        expect(wrapper.text()).toContain("settings.android_privacy_heading");
        expect(wrapper.text()).toContain("settings.android_remote_backend_heading");
        const checkboxes = wrapper.findAll('input[type="checkbox"]');
        expect(checkboxes).toHaveLength(2);
        await checkboxes[0].setValue(true);
        await checkboxes[1].setValue(true);
        expect(wrapper.emitted("update:blockScreenshots")).toEqual([[true]]);
        expect(wrapper.emitted("update:clearClipboardOnBackground")).toEqual([[true]]);
        const urlInput = wrapper.find('input[type="url"]');
        await urlInput.setValue("http://192.168.1.10:9337");
        expect(wrapper.emitted("update:remoteBackendUrl")?.at(-1)).toEqual(["http://192.168.1.10:9337"]);
        const buttons = wrapper.findAll("button");
        await buttons[0].trigger("click");
        expect(wrapper.emitted("apply-remote-backend")).toHaveLength(1);
        await buttons[2].trigger("click");
        expect(wrapper.emitted("share-apk")).toHaveLength(1);
    });
});

describe("ArchiverSettingsSection", () => {
    it("emits enabled-change, config-change, and flush", async () => {
        const wrapper = mount(ArchiverSettingsSection, {
            props: {
                visible: true,
                config: {
                    page_archiver_enabled: false,
                    page_archiver_max_versions: 5,
                    archives_max_storage_gb: 2,
                },
            },
        });
        expect(wrapper.text()).toContain("Page Archiver");
        await wrapper.findComponent({ name: "Toggle" }).vm.$emit("update:modelValue", true);
        expect(wrapper.emitted("enabled-change")).toEqual([[true]]);
        const numberInputs = wrapper.findAll('input[type="number"]');
        await numberInputs[0].setValue(8);
        expect(wrapper.emitted("config-change")?.at(-1)).toEqual([{ page_archiver_max_versions: 8 }]);
        await wrapper.find("button").trigger("click");
        expect(wrapper.emitted("flush")).toHaveLength(1);
    });
});
