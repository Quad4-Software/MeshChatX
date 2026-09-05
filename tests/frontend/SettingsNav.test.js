// SPDX-License-Identifier: 0BSD

import { render, fireEvent } from "@testing-library/svelte";
import { describe, expect, it, vi } from "vitest";
import SettingsNav from "../../meshchatx/src/frontend/features/settings/components/SettingsNav.svelte";
import { SETTINGS_TABS } from "../../meshchatx/src/frontend/js/settings/settingsTabs.js";
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
