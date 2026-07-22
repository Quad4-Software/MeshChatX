// SPDX-License-Identifier: 0BSD

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import SettingToggleRow from "../../meshchatx/src/frontend/components/settings/SettingToggleRow.vue";
import StrangerProtectionSettingsSection from "../../meshchatx/src/frontend/components/settings/sections/StrangerProtectionSettingsSection.vue";
import BanishmentSettingsSection from "../../meshchatx/src/frontend/components/settings/sections/BanishmentSettingsSection.vue";
import TelephonySettingsSection from "../../meshchatx/src/frontend/components/settings/sections/TelephonySettingsSection.vue";

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
