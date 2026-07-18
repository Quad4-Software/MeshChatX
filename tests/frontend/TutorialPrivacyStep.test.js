// SPDX-License-Identifier: 0BSD

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createI18n } from "vue-i18n";
import { createVuetify } from "vuetify";
import TutorialPrivacyStep from "../../meshchatx/src/frontend/components/TutorialPrivacyStep.vue";
import en from "../../meshchatx/src/frontend/locales/en.json";
import ElectronUtils from "../../meshchatx/src/frontend/js/ElectronUtils.js";
import { CORE_POST_INSTALL_PROMPT_ENTRIES } from "../../meshchatx/src/frontend/js/registries/corePostInstallPromptEntries.js";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils";

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
    },
}));

const vuetify = createVuetify();
const i18n = createI18n({
    legacy: false,
    locale: "en",
    messages: { en },
});

function mountPrivacyStep() {
    return mount(TutorialPrivacyStep, {
        global: {
            plugins: [i18n, vuetify],
            stubs: { Toggle: true },
        },
    });
}

describe("TutorialPrivacyStep", () => {
    beforeEach(() => {
        window.api = {
            get: vi.fn(async (url) => {
                if (url === "/api/v1/config") {
                    return {
                        data: {
                            config: {
                                privacy_mode_enabled: false,
                                telemetry_enabled: true,
                            },
                        },
                    };
                }
                if (url === "/api/v1/reticulum/instance") {
                    return {
                        data: {
                            instance: {
                                local_hops_delta: false,
                            },
                        },
                    };
                }
                return { data: {} };
            }),
            patch: vi.fn(async () => ({ data: {} })),
        };
        vi.spyOn(ElectronUtils, "isWindowsElectron").mockReturnValue(false);
    });

    afterEach(() => {
        vi.restoreAllMocks();
        delete window.api;
        delete window.electron;
    });

    it("loads privacy toggles and patches obfuscate hops", async () => {
        const wrapper = mountPrivacyStep();
        await flushPromises();
        expect(wrapper.vm.localHopsDelta).toBe(false);
        expect(wrapper.vm.privacyModeEnabled).toBe(false);
        expect(wrapper.vm.telemetryEnabled).toBe(true);
        expect(wrapper.vm.showWindowsScreenSecurity).toBe(false);

        await wrapper.vm.onLocalHopsDeltaChange(true);
        expect(window.api.patch).toHaveBeenCalledWith("/api/v1/reticulum/instance", {
            local_hops_delta: true,
        });
        expect(wrapper.vm.localHopsDelta).toBe(true);
    });

    it("shows Windows DRM screen security when on Windows Electron", async () => {
        ElectronUtils.isWindowsElectron.mockReturnValue(true);
        vi.spyOn(ElectronUtils, "getScreenSecuritySettings").mockResolvedValue({
            platform: "win32",
            available: true,
            windowsDrm: true,
            enabled: false,
        });
        vi.spyOn(ElectronUtils, "setScreenSecurityEnabled").mockResolvedValue({
            platform: "win32",
            available: true,
            windowsDrm: true,
            enabled: true,
        });

        const wrapper = mountPrivacyStep();
        await flushPromises();
        expect(wrapper.vm.showWindowsScreenSecurity).toBe(true);
        expect(wrapper.text()).toContain("Windows DRM");

        await wrapper.vm.onScreenSecurityChange(true);
        expect(ElectronUtils.setScreenSecurityEnabled).toHaveBeenCalledWith(true);
        expect(ToastUtils.success).toHaveBeenCalled();
        expect(wrapper.vm.screenSecurityEnabled).toBe(true);
    });

    it("tolerates load failures and missing payload fields", async () => {
        window.api.get = vi.fn(async () => {
            throw new Error("offline");
        });
        const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});
        const wrapper = mountPrivacyStep();
        await flushPromises();
        expect(wrapper.vm.privacyModeEnabled).toBe(false);
        expect(wrapper.vm.localHopsDelta).toBe(false);
        expect(wrapper.vm.telemetryEnabled).toBe(false);
        errSpy.mockRestore();
    });

    it("rolls back obfuscate hops when patch fails", async () => {
        const wrapper = mountPrivacyStep();
        await flushPromises();
        window.api.patch = vi.fn(async () => {
            throw new Error("patch failed");
        });
        const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});
        await wrapper.vm.onLocalHopsDeltaChange(true);
        expect(wrapper.vm.localHopsDelta).toBe(false);
        expect(ToastUtils.error).toHaveBeenCalled();
        errSpy.mockRestore();
    });

    it("dedupes concurrent screen-security toggles (race)", async () => {
        ElectronUtils.isWindowsElectron.mockReturnValue(true);
        vi.spyOn(ElectronUtils, "getScreenSecuritySettings").mockResolvedValue({
            enabled: false,
            available: true,
        });
        let resolveSet;
        const setSpy = vi.spyOn(ElectronUtils, "setScreenSecurityEnabled").mockImplementation(
            () =>
                new Promise((resolve) => {
                    resolveSet = resolve;
                })
        );

        const wrapper = mountPrivacyStep();
        await flushPromises();

        const first = wrapper.vm.onScreenSecurityChange(true);
        const second = wrapper.vm.onScreenSecurityChange(false);
        expect(setSpy).toHaveBeenCalledTimes(1);

        resolveSet({ enabled: true });
        await Promise.all([first, second]);
        expect(wrapper.vm.screenSecurityEnabled).toBe(true);
        expect(wrapper.vm.screenSecuritySaving).toBe(false);
    });

    it("dedupes concurrent obfuscate-hops patches (race)", async () => {
        const wrapper = mountPrivacyStep();
        await flushPromises();

        let resolvePatch;
        window.api.patch = vi.fn(
            () =>
                new Promise((resolve) => {
                    resolvePatch = resolve;
                })
        );

        const first = wrapper.vm.onLocalHopsDeltaChange(true);
        const second = wrapper.vm.onLocalHopsDeltaChange(false);
        expect(window.api.patch).toHaveBeenCalledTimes(1);

        resolvePatch({ data: {} });
        await Promise.all([first, second]);
        expect(wrapper.vm.localHopsDelta).toBe(true);
        expect(wrapper.vm.reticulumSaving).toBe(false);
    });

    it("dedupes concurrent privacy-mode and telemetry patches sharing configSaving", async () => {
        const wrapper = mountPrivacyStep();
        await flushPromises();

        let resolvePatch;
        window.api.patch = vi.fn(
            () =>
                new Promise((resolve) => {
                    resolvePatch = resolve;
                })
        );

        const privacy = wrapper.vm.onPrivacyModeChange(true);
        const telemetry = wrapper.vm.onTelemetryChange(false);
        expect(window.api.patch).toHaveBeenCalledTimes(1);
        expect(window.api.patch.mock.calls[0][1]).toEqual({ privacy_mode_enabled: true });

        resolvePatch({ data: {} });
        await Promise.all([privacy, telemetry]);
        expect(wrapper.vm.privacyModeEnabled).toBe(true);
        expect(wrapper.vm.telemetryEnabled).toBe(true);
        expect(wrapper.vm.configSaving).toBe(false);
    });

    it("rolls back screen security when set fails", async () => {
        ElectronUtils.isWindowsElectron.mockReturnValue(true);
        vi.spyOn(ElectronUtils, "getScreenSecuritySettings").mockResolvedValue({ enabled: false });
        vi.spyOn(ElectronUtils, "setScreenSecurityEnabled").mockRejectedValue(new Error("ipc down"));
        const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});

        const wrapper = mountPrivacyStep();
        await flushPromises();
        await wrapper.vm.onScreenSecurityChange(true);
        expect(wrapper.vm.screenSecurityEnabled).toBe(false);
        expect(ToastUtils.error).toHaveBeenCalled();
        errSpy.mockRestore();
    });
});

describe("windows_screen_security post-install prompt", () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("is registered with enable/later actions", () => {
        const entry = CORE_POST_INSTALL_PROMPT_ENTRIES.find((e) => e.id === "windows_screen_security");
        expect(entry).toBeTruthy();
        expect(entry.revision).toBe(1);
        expect(entry.titleKey).toBe("post_install.windows_screen_security_title");
        expect(entry.primaryLabelKey).toBe("post_install.windows_screen_security_enable");
        expect(entry.secondaryLabelKey).toBe("post_install.windows_screen_security_later");
    });

    it("shouldShow is false off Windows Electron", async () => {
        const entry = CORE_POST_INSTALL_PROMPT_ENTRIES.find((e) => e.id === "windows_screen_security");
        vi.spyOn(ElectronUtils, "isWindowsElectron").mockReturnValue(false);
        await expect(entry.shouldShow()).resolves.toBe(false);
    });

    it("shouldShow is true when Windows Electron and disabled", async () => {
        const entry = CORE_POST_INSTALL_PROMPT_ENTRIES.find((e) => e.id === "windows_screen_security");
        vi.spyOn(ElectronUtils, "isWindowsElectron").mockReturnValue(true);
        vi.spyOn(ElectronUtils, "getScreenSecuritySettings").mockResolvedValue({
            available: true,
            enabled: false,
        });
        await expect(entry.shouldShow()).resolves.toBe(true);
    });

    it("shouldShow is false when already enabled or unavailable", async () => {
        const entry = CORE_POST_INSTALL_PROMPT_ENTRIES.find((e) => e.id === "windows_screen_security");
        vi.spyOn(ElectronUtils, "isWindowsElectron").mockReturnValue(true);
        vi.spyOn(ElectronUtils, "getScreenSecuritySettings").mockResolvedValue({
            available: true,
            enabled: true,
        });
        await expect(entry.shouldShow()).resolves.toBe(false);

        ElectronUtils.getScreenSecuritySettings.mockResolvedValue({
            available: false,
            enabled: false,
        });
        await expect(entry.shouldShow()).resolves.toBe(false);
    });

    it("shouldShow is false when settings lookup throws", async () => {
        const entry = CORE_POST_INSTALL_PROMPT_ENTRIES.find((e) => e.id === "windows_screen_security");
        vi.spyOn(ElectronUtils, "isWindowsElectron").mockReturnValue(true);
        vi.spyOn(ElectronUtils, "getScreenSecuritySettings").mockRejectedValue(new Error("boom"));
        await expect(entry.shouldShow()).resolves.toBe(false);
    });

    it("onPrimary enables screen security", async () => {
        const entry = CORE_POST_INSTALL_PROMPT_ENTRIES.find((e) => e.id === "windows_screen_security");
        const setSpy = vi.spyOn(ElectronUtils, "setScreenSecurityEnabled").mockResolvedValue({ enabled: true });
        await expect(entry.onPrimary()).resolves.toBe(true);
        expect(setSpy).toHaveBeenCalledWith(true);
    });

    it("onPrimary returns false when enable fails", async () => {
        const entry = CORE_POST_INSTALL_PROMPT_ENTRIES.find((e) => e.id === "windows_screen_security");
        vi.spyOn(ElectronUtils, "setScreenSecurityEnabled").mockRejectedValue(new Error("fail"));
        const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});
        await expect(entry.onPrimary()).resolves.toBe(false);
        errSpy.mockRestore();
    });

    it("shouldShow tolerates missing isWindowsElectron helper", async () => {
        const entry = CORE_POST_INSTALL_PROMPT_ENTRIES.find((e) => e.id === "windows_screen_security");
        const original = ElectronUtils.isWindowsElectron;
        // Simulate partial ElectronUtils mock used in other tests.
        // @ts-ignore
        ElectronUtils.isWindowsElectron = undefined;
        await expect(entry.shouldShow()).resolves.toBe(false);
        ElectronUtils.isWindowsElectron = original;
    });
});
