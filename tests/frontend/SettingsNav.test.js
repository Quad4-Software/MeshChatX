// SPDX-License-Identifier: 0BSD

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import SettingsNav from "../../meshchatx/src/frontend/components/settings/SettingsNav.vue";
import { SETTINGS_TABS } from "../../meshchatx/src/frontend/js/settings/settingsTabs.js";

describe("SettingsNav", () => {
    function mountNav(activeTab = "general") {
        return mount(SettingsNav, {
            props: { activeTab },
            global: {
                mocks: {
                    $t: (key) => key,
                },
            },
        });
    }

    it("renders every settings tab", () => {
        const wrapper = mountNav();
        const tabs = wrapper.findAll(".settings-nav__tab");
        expect(tabs).toHaveLength(SETTINGS_TABS.length);
        for (const tab of SETTINGS_TABS) {
            expect(wrapper.text()).toContain(tab.labelKey);
        }
    });

    it("marks the active tab with aria-current", () => {
        const wrapper = mountNav("privacy");
        const active = wrapper.find('[aria-current="page"]');
        expect(active.exists()).toBe(true);
        expect(active.text()).toContain("settings.tabs.privacy");
    });

    it("emits select when a tab is clicked", async () => {
        const wrapper = mountNav("general");
        const buttons = wrapper.findAll(".settings-nav__tab");
        const networkButton = buttons.find((btn) => btn.text().includes("settings.tabs.network"));
        expect(networkButton).toBeDefined();
        await networkButton.trigger("click");
        expect(wrapper.emitted("select")).toEqual([["network"]]);
    });

    it("exposes an accessible navigation landmark", () => {
        const wrapper = mountNav();
        const nav = wrapper.find("nav.settings-nav");
        expect(nav.attributes("aria-label")).toBe("settings.nav_label");
    });

    it("shows match counts during search and disables empty tabs", async () => {
        const wrapper = mount(SettingsNav, {
            props: {
                activeTab: "",
                matchCounts: { general: 2, messages: 0, network: 1 },
            },
            global: {
                mocks: {
                    $t: (key) => key,
                },
            },
        });
        const buttons = wrapper.findAll(".settings-nav__tab");
        const general = buttons.find((btn) => btn.text().includes("settings.tabs.general"));
        const messages = buttons.find((btn) => btn.text().includes("settings.tabs.messages"));
        expect(general).toBeDefined();
        expect(messages).toBeDefined();
        expect(general.text()).toContain("2");
        expect(messages.attributes("disabled")).toBeDefined();
        await general.trigger("click");
        expect(wrapper.emitted("select")).toEqual([["general"]]);
        await messages.trigger("click");
        expect(wrapper.emitted("select")).toEqual([["general"]]);
    });
});
