// SPDX-License-Identifier: 0BSD

import { render, fireEvent, waitFor } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import SettingsPage from "../../meshchatx/src/frontend/features/settings/components/SettingsPage.svelte";
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

async function renderPrivacyTab() {
    const api = createWindowApi(buildFullServerConfig());
    window.api = api;
    const view = render(SettingsPage);
    const tabs = view.container.querySelectorAll(".settings-nav__tab");
    for (const tab of tabs) {
        if (tab.textContent.includes("Privacy")) {
            await fireEvent.click(tab);
            break;
        }
    }
    return view;
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
        const { container } = await renderPrivacyTab();
        await waitFor(() => {
            expect(ElectronUtils.getScreenSecuritySettings).toHaveBeenCalled();
            const toggle = container.querySelector("#screen-security-enabled");
            expect(toggle).not.toBeNull();
            expect(toggle.checked).toBe(false);
        });
    });

    it("hides screen security when not Windows Electron", async () => {
        ElectronUtils.isWindowsElectron.mockReturnValue(false);
        const { container } = await renderPrivacyTab();
        await waitFor(() => {
            expect(ElectronUtils.getScreenSecuritySettings).not.toHaveBeenCalled();
            const toggle = container.querySelector("#screen-security-enabled");
            expect(toggle).toBeNull();
        });
    });

    it("tolerates getScreenSecuritySettings failures", async () => {
        ElectronUtils.getScreenSecuritySettings.mockRejectedValue(new Error("ipc"));
        const logSpy = vi.spyOn(console, "log").mockImplementation(() => {});
        const { container } = await renderPrivacyTab();
        await waitFor(() => {
            const toggle = container.querySelector("#screen-security-enabled");
            expect(toggle).not.toBeNull();
            expect(toggle.checked).toBe(false);
        });
        logSpy.mockRestore();
    });

    it("cancels disable when confirm is rejected", async () => {
        ElectronUtils.getScreenSecuritySettings.mockResolvedValue({
            enabled: true,
            available: true,
        });
        DialogUtils.confirm.mockResolvedValue(false);
        const { container } = await renderPrivacyTab();

        await waitFor(() => {
            const toggle = container.querySelector("#screen-security-enabled");
            expect(toggle).not.toBeNull();
            expect(toggle.checked).toBe(true);
        });

        const toggle = container.querySelector("#screen-security-enabled");
        await fireEvent.click(toggle);

        await waitFor(() => {
            expect(DialogUtils.confirm).toHaveBeenCalled();
            expect(ElectronUtils.setScreenSecurityEnabled).not.toHaveBeenCalled();
            expect(toggle.checked).toBe(true);
        });
    });

    it("rolls back and toasts when setScreenSecurityEnabled fails", async () => {
        ElectronUtils.setScreenSecurityEnabled.mockRejectedValue(new Error("fail"));
        const logSpy = vi.spyOn(console, "log").mockImplementation(() => {});
        const { container } = await renderPrivacyTab();

        await waitFor(() => {
            const toggle = container.querySelector("#screen-security-enabled");
            expect(toggle).not.toBeNull();
            expect(toggle.checked).toBe(false);
        });

        const toggle = container.querySelector("#screen-security-enabled");
        await fireEvent.click(toggle);

        await waitFor(() => {
            expect(ToastUtils.error).toHaveBeenCalled();
            expect(toggle.checked).toBe(false);
        });
        logSpy.mockRestore();
    });

    it("tolerates missing isWindowsElectron on ElectronUtils mock", async () => {
        const original = ElectronUtils.isWindowsElectron;
        // @ts-ignore
        ElectronUtils.isWindowsElectron = undefined;
        const { container } = await renderPrivacyTab();
        const toggle = container.querySelector("#screen-security-enabled");
        expect(toggle).toBeNull();
        ElectronUtils.isWindowsElectron = original;
    });
});
