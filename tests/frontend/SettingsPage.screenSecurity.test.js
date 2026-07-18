// SPDX-License-Identifier: 0BSD

import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import SettingsPage from "../../meshchatx/src/frontend/components/settings/SettingsPage.vue";
import Toggle from "../../meshchatx/src/frontend/components/forms/Toggle.vue";
import DialogUtils from "../../meshchatx/src/frontend/js/DialogUtils";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils";
import ElectronUtils from "../../meshchatx/src/frontend/js/ElectronUtils";
import { buildFullServerConfig, createWindowApi } from "./fixtures/settingsPageTestApi.js";

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
        isElectron: vi.fn(() => true),
        isWindowsElectron: vi.fn(() => true),
        getScreenSecuritySettings: vi.fn(async () => ({
            platform: "win32",
            available: true,
            windowsDrm: true,
            enabled: false,
        })),
        setScreenSecurityEnabled: vi.fn(async (enabled) => ({
            platform: "win32",
            available: true,
            windowsDrm: true,
            enabled: enabled === true,
        })),
        getCloseSettings: vi.fn(async () => ({ closeBehavior: "ask", trayEnabled: true })),
        setCloseSettings: vi.fn(async (partial) => ({
            closeBehavior: "ask",
            trayEnabled: true,
            ...partial,
        })),
    },
}));

async function mountSettingsPage() {
    const api = createWindowApi(buildFullServerConfig());
    window.api = api;
    const wrapper = mount(SettingsPage, {
        global: {
            stubs: {
                MaterialDesignIcon: { template: "<span class='mdi'></span>" },
                Toggle,
                SettingsNav: true,
                LanguageSelector: true,
                PluginSlotNode: true,
            },
            mocks: {
                $t: (key) => key,
                $router: { push: vi.fn() },
                $route: { name: "settings", query: {} },
            },
        },
    });
    await flushPromises();
    return wrapper;
}

describe("SettingsPage screen security edge and race", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        ElectronUtils.isWindowsElectron.mockReturnValue(true);
        ElectronUtils.getScreenSecuritySettings.mockResolvedValue({
            platform: "win32",
            available: true,
            windowsDrm: true,
            enabled: false,
        });
        ElectronUtils.setScreenSecurityEnabled.mockImplementation(async (enabled) => ({
            platform: "win32",
            available: true,
            windowsDrm: true,
            enabled: enabled === true,
        }));
        DialogUtils.confirm.mockResolvedValue(true);
    });

    afterEach(() => {
        delete window.api;
    });

    it("loads Windows screen security state on mount", async () => {
        const wrapper = await mountSettingsPage();
        expect(wrapper.vm.showWindowsScreenSecurity).toBe(true);
        expect(wrapper.vm.screenSecurityEnabled).toBe(false);
        expect(ElectronUtils.getScreenSecuritySettings).toHaveBeenCalled();
        wrapper.unmount();
    });

    it("hides screen security when not Windows Electron", async () => {
        ElectronUtils.isWindowsElectron.mockReturnValue(false);
        const wrapper = await mountSettingsPage();
        expect(wrapper.vm.showWindowsScreenSecurity).toBe(false);
        expect(ElectronUtils.getScreenSecuritySettings).not.toHaveBeenCalled();
        wrapper.unmount();
    });

    it("tolerates getScreenSecuritySettings failures", async () => {
        ElectronUtils.getScreenSecuritySettings.mockRejectedValue(new Error("ipc"));
        const logSpy = vi.spyOn(console, "log").mockImplementation(() => {});
        const wrapper = await mountSettingsPage();
        expect(wrapper.vm.showWindowsScreenSecurity).toBe(true);
        expect(wrapper.vm.screenSecurityEnabled).toBe(false);
        logSpy.mockRestore();
        wrapper.unmount();
    });

    it("cancels disable when confirm is rejected", async () => {
        ElectronUtils.getScreenSecuritySettings.mockResolvedValue({
            enabled: true,
            available: true,
        });
        DialogUtils.confirm.mockResolvedValue(false);
        const wrapper = await mountSettingsPage();
        expect(wrapper.vm.screenSecurityEnabled).toBe(true);

        await wrapper.vm.onScreenSecurityChange(false);
        expect(DialogUtils.confirm).toHaveBeenCalled();
        expect(ElectronUtils.setScreenSecurityEnabled).not.toHaveBeenCalled();
        expect(wrapper.vm.screenSecurityEnabled).toBe(true);
        wrapper.unmount();
    });

    it("dedupes concurrent enable toggles (race)", async () => {
        let resolveSet;
        ElectronUtils.setScreenSecurityEnabled.mockImplementation(
            () =>
                new Promise((resolve) => {
                    resolveSet = resolve;
                })
        );
        const wrapper = await mountSettingsPage();

        const first = wrapper.vm.onScreenSecurityChange(true);
        const second = wrapper.vm.onScreenSecurityChange(true);
        expect(ElectronUtils.setScreenSecurityEnabled).toHaveBeenCalledTimes(1);

        resolveSet({ enabled: true, available: true, platform: "win32", windowsDrm: true });
        await Promise.all([first, second]);
        expect(wrapper.vm.screenSecurityEnabled).toBe(true);
        expect(wrapper.vm.screenSecuritySaving).toBe(false);
        wrapper.unmount();
    });

    it("holds the race lock across disable confirm", async () => {
        let resolveConfirm;
        DialogUtils.confirm.mockImplementation(
            () =>
                new Promise((resolve) => {
                    resolveConfirm = resolve;
                })
        );
        ElectronUtils.getScreenSecuritySettings.mockResolvedValue({
            enabled: true,
            available: true,
        });
        const wrapper = await mountSettingsPage();

        const first = wrapper.vm.onScreenSecurityChange(false);
        const second = wrapper.vm.onScreenSecurityChange(false);
        expect(DialogUtils.confirm).toHaveBeenCalledTimes(1);

        resolveConfirm(true);
        await flushPromises();
        await Promise.all([first, second]);
        expect(ElectronUtils.setScreenSecurityEnabled).toHaveBeenCalledTimes(1);
        expect(ElectronUtils.setScreenSecurityEnabled).toHaveBeenCalledWith(false);
        wrapper.unmount();
    });

    it("rolls back and toasts when setScreenSecurityEnabled fails", async () => {
        ElectronUtils.setScreenSecurityEnabled.mockRejectedValue(new Error("fail"));
        const logSpy = vi.spyOn(console, "log").mockImplementation(() => {});
        const wrapper = await mountSettingsPage();
        await wrapper.vm.onScreenSecurityChange(true);
        expect(wrapper.vm.screenSecurityEnabled).toBe(false);
        expect(ToastUtils.error).toHaveBeenCalled();
        logSpy.mockRestore();
        wrapper.unmount();
    });

    it("tolerates missing isWindowsElectron on ElectronUtils mock", async () => {
        const original = ElectronUtils.isWindowsElectron;
        // @ts-ignore
        ElectronUtils.isWindowsElectron = undefined;
        const wrapper = await mountSettingsPage();
        expect(wrapper.vm.showWindowsScreenSecurity).toBe(false);
        ElectronUtils.isWindowsElectron = original;
        wrapper.unmount();
    });
});
