// SPDX-License-Identifier: 0BSD

import { render, fireEvent } from "@testing-library/svelte";
import { describe, expect, it, vi } from "vitest";
import SettingsNav from "../../meshchatx/src/frontend/features/settings/components/SettingsNav.svelte";
import {
    getSettingsTab,
    SETTINGS_TABS,
    settingsTabHasVisibleSections,
} from "../../meshchatx/src/frontend/js/settings/settingsTabs.js";
import { t } from "../../meshchatx/src/frontend/js/i18n.js";

describe("SettingsNav", () => {
    function renderNav(activeTab = "general", props = {}) {
        return render(SettingsNav, {
            props: { activeTab, ...props },
        });
    }

    it("renders every settings tab", () => {
        const { container } = renderNav();
        const tabs = container.querySelectorAll(".settings-nav__tab");
        expect(tabs).toHaveLength(SETTINGS_TABS.length);
        for (const tab of SETTINGS_TABS) {
            expect(container.textContent).toContain(t(tab.labelKey));
        }
    });

    it("marks the active tab with aria-current", () => {
        const { container } = renderNav("privacy");
        const active = container.querySelector('[aria-current="page"]');
        expect(active).not.toBeNull();
        expect(active.textContent).toContain(t("settings.tabs.privacy"));
    });

    it("emits select when a tab is clicked", async () => {
        const onselect = vi.fn();
        const { container } = renderNav("general", { onselect });
        const buttons = Array.from(container.querySelectorAll(".settings-nav__tab"));
        const networkButton = buttons.find((btn) => btn.textContent.includes(t("settings.tabs.network")));
        expect(networkButton).toBeDefined();
        await fireEvent.click(networkButton);
        expect(onselect).toHaveBeenCalledWith("network");
    });

    it("exposes an accessible navigation landmark", () => {
        const { container } = renderNav();
        const nav = container.querySelector("nav.settings-nav");
        expect(nav.getAttribute("aria-label")).toBe(t("settings.nav_label"));
    });

    it("hides all-advanced tabs in simple mode and shows them in advanced mode", () => {
        // SettingsNav renders every tab it is given; simple/advanced
        // filtering lives in the settingsTabs helpers used by the page.
        const { container } = renderNav("general");
        expect(container.querySelectorAll(".settings-nav__tab")).toHaveLength(SETTINGS_TABS.length);

        const hiddenInSimple = SETTINGS_TABS.filter((tab) => !settingsTabHasVisibleSections(tab, "simple")).map(
            (tab) => tab.id
        );
        expect(hiddenInSimple).toEqual(["network", "nomad", "plugins"]);
        expect(settingsTabHasVisibleSections(getSettingsTab("general"), "simple")).toBe(true);
        expect(settingsTabHasVisibleSections(getSettingsTab("privacy"), "simple")).toBe(true);
        for (const tab of SETTINGS_TABS) {
            expect(settingsTabHasVisibleSections(tab, "advanced")).toBe(true);
        }
    });

    it("emits select through the onselecttab callback prop", async () => {
        const onselecttab = vi.fn();
        const { container } = renderNav("general", { onselecttab });
        const buttons = Array.from(container.querySelectorAll(".settings-nav__tab"));
        const networkButton = buttons.find((btn) => btn.textContent.includes(t("settings.tabs.network")));
        expect(networkButton).toBeDefined();
        await fireEvent.click(networkButton);
        expect(onselecttab).toHaveBeenCalledWith("network");
    });

    it("keeps every tab reachable during search", () => {
        const { container } = renderNav("", {
            matchCounts: { general: 0, network: 1 },
        });
        const buttons = Array.from(container.querySelectorAll(".settings-nav__tab"));
        expect(buttons).toHaveLength(SETTINGS_TABS.length);
        const networkButton = buttons.find((btn) => btn.textContent.includes(t("settings.tabs.network")));
        expect(networkButton).toBeDefined();
        expect(networkButton.disabled).toBe(false);
    });

    it("shows match counts during search and disables empty tabs", async () => {
        const onselect = vi.fn();
        const { container } = renderNav("", {
            matchCounts: { general: 2, messages: 0, network: 1 },
            onselect,
        });
        const buttons = Array.from(container.querySelectorAll(".settings-nav__tab"));
        const general = buttons.find((btn) => btn.textContent.includes(t("settings.tabs.general")));
        const messages = buttons.find((btn) => btn.textContent.includes(t("settings.tabs.messages")));
        expect(general).toBeDefined();
        expect(messages).toBeDefined();
        expect(general.textContent).toContain("2");
        expect(messages.disabled).toBe(true);
        await fireEvent.click(general);
        expect(onselect).toHaveBeenCalledWith("general");
        onselect.mockClear();
        await fireEvent.click(messages);
        expect(onselect).not.toHaveBeenCalled();
    });
});
