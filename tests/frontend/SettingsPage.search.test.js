// SPDX-License-Identifier: 0BSD

import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import SettingsPage from "../../meshchatx/src/frontend/components/settings/SettingsPage.vue";
import Toggle from "../../meshchatx/src/frontend/components/forms/Toggle.vue";
import GlobalState from "../../meshchatx/src/frontend/js/GlobalState";
import { createWindowApi, buildFullServerConfig } from "./fixtures/settingsPageTestApi.js";
import { registerCoreContributions } from "../../meshchatx/src/frontend/js/registries/registerCoreContributions.js";

registerCoreContributions();

vi.mock("../../meshchatx/src/frontend/js/WebSocketConnection", () => ({
    default: {
        on: vi.fn(),
        off: vi.fn(),
        emit: vi.fn(),
        send: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
        loading: vi.fn(),
        dismiss: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn().mockResolvedValue(true),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/KeyboardShortcuts", () => ({
    default: {
        getDefaultShortcuts: vi.fn(() => []),
        send: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/ElectronUtils", () => ({
    default: {
        isElectron: vi.fn(() => false),
        isWindowsElectron: vi.fn(() => false),
        getScreenSecuritySettings: vi.fn(async () => null),
        setScreenSecurityEnabled: vi.fn(async () => null),
        getCloseSettings: vi.fn(async () => null),
        setCloseSettings: vi.fn(async () => null),
    },
}));

async function mountSettingsPage() {
    window.api = createWindowApi({ current: buildFullServerConfig() });
    const wrapper = mount(SettingsPage, {
        attachTo: document.body,
        global: {
            stubs: {
                MaterialDesignIcon: { template: "<span class='mdi'></span>" },
                Toggle,
                ShortcutRecorder: { template: "<div></div>" },
                RouterLink: { template: "<a><slot /></a>" },
                SettingsSectionBlock: { template: "<div class='settings-section-block'><slot /></div>" },
            },
            mocks: {
                $t: (key, params) => {
                    if (params?.query) return `${key}:${params.query}`;
                    if (params?.n != null) return `${key}:${params.n}`;
                    return key;
                },
                $router: { push: vi.fn() },
            },
        },
    });
    await flushPromises();
    await wrapper.vm.$nextTick();
    return wrapper;
}

describe("SettingsPage search", () => {
    /** @type {import("@vue/test-utils").VueWrapper | null} */
    let wrapper;

    beforeEach(() => {
        registerCoreContributions();
        GlobalState.pluginsEnabled = true;
        wrapper = null;
    });

    afterEach(() => {
        wrapper?.unmount();
        wrapper = null;
        GlobalState.pluginsEnabled = true;
        delete window.api;
        vi.clearAllMocks();
        document.body.innerHTML = "";
    });

    it("empty query shows the active tab only", async () => {
        wrapper = await mountSettingsPage();
        expect(wrapper.vm.showSection("appearance")).toBe(true);
        expect(wrapper.vm.showSection("messages")).toBe(false);
        expect(wrapper.vm.hasSearchResults).toBe(true);
    });

    it("filters sections by keyword and shows the empty state when nothing matches", async () => {
        wrapper = await mountSettingsPage();
        wrapper.vm.searchQuery = "theme";
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.settingsSearchActive).toBe(true);
        expect(wrapper.vm.showSection("appearance")).toBe(true);
        expect(wrapper.vm.showSection("maintenance")).toBe(false);
        expect(wrapper.vm.hasSearchResults).toBe(true);

        wrapper.vm.searchQuery = "zzz-no-such-setting";
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.hasSearchResults).toBe(false);
        expect(wrapper.text()).toContain("settings.search_no_results");
        expect(wrapper.text()).toContain("settings.search_no_match:zzz-no-such-setting");
    });

    it("matches a tab label across that tab's sections", async () => {
        wrapper = await mountSettingsPage();
        wrapper.vm.searchQuery = "network";
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.showSection("transport")).toBe(true);
        expect(wrapper.vm.showSection("interfaces")).toBe(true);
        expect(wrapper.vm.showSection("telephony")).toBe(true);
        expect(wrapper.vm.showSection("appearance")).toBe(false);
        expect(wrapper.vm.settingsSearchMatchCounts.network).toBeGreaterThan(0);
        expect(wrapper.vm.settingsSearchMatchCounts.general).toBe(0);
    });

    it("matches hyphenated and compact queries", async () => {
        wrapper = await mountSettingsPage();
        wrapper.vm.searchQuery = "dark-mode";
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.showSection("appearance")).toBe(true);

        wrapper.vm.searchQuery = "darkmode";
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.showSection("appearance")).toBe(true);
    });

    it("clicking a matching tab during search filters to that tab", async () => {
        wrapper = await mountSettingsPage();
        wrapper.vm.searchQuery = "privacy";
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.showSection("privacyData")).toBe(true);
        expect(wrapper.vm.showSection("csp")).toBe(true);
        wrapper.vm.onSettingsNavSelect("privacy");
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.searchTabFilter).toBe("privacy");
        expect(wrapper.vm.showSection("privacyData")).toBe(true);
        wrapper.vm.onSettingsNavSelect("privacy");
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.searchTabFilter).toBeNull();
    });

    it("hides plugins matches when plugins are disabled", async () => {
        GlobalState.pluginsEnabled = false;
        wrapper = await mountSettingsPage();
        wrapper.vm.searchQuery = "plugins";
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.showSection("plugins")).toBe(false);
        expect(wrapper.vm.settingsSearchMatchCounts.plugins).toBe(0);
    });

    it("slash focuses the search field when not typing in an input", async () => {
        wrapper = await mountSettingsPage();
        const input = wrapper.find('input[type="search"]');
        expect(input.exists()).toBe(true);
        window.dispatchEvent(new KeyboardEvent("keydown", { key: "/", bubbles: true }));
        await wrapper.vm.$nextTick();
        expect(document.activeElement).toBe(input.element);
    });

    it("clearSettingsSearch restores tab browsing", async () => {
        wrapper = await mountSettingsPage();
        wrapper.vm.searchQuery = "theme";
        wrapper.vm.searchTabFilter = "general";
        await wrapper.vm.$nextTick();
        wrapper.vm.clearSettingsSearch();
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.searchQuery).toBe("");
        expect(wrapper.vm.searchTabFilter).toBeNull();
        expect(wrapper.vm.settingsSearchActive).toBe(false);
        expect(wrapper.vm.showSection("appearance")).toBe(true);
    });
});
