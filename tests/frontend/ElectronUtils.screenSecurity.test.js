// SPDX-License-Identifier: 0BSD

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import ElectronUtils from "../../meshchatx/src/frontend/js/ElectronUtils.js";

describe("ElectronUtils screen security edge cases", () => {
    afterEach(() => {
        delete window.electron;
        vi.restoreAllMocks();
    });

    it("returns nulls when electron bridge is missing", async () => {
        expect(ElectronUtils.isElectron()).toBe(false);
        expect(ElectronUtils.getPlatform()).toBeNull();
        expect(ElectronUtils.isWindowsElectron()).toBe(false);
        await expect(ElectronUtils.getScreenSecuritySettings()).resolves.toBeNull();
        await expect(ElectronUtils.setScreenSecurityEnabled(true)).resolves.toBeNull();
    });

    it("isWindowsElectron requires both electron and win32", () => {
        window.electron = {
            getPlatform: () => "linux",
        };
        expect(ElectronUtils.isWindowsElectron()).toBe(false);
        window.electron.getPlatform = () => "win32";
        expect(ElectronUtils.isWindowsElectron()).toBe(true);
    });

    it("coerces setScreenSecurityEnabled to a strict boolean for the IPC bridge", async () => {
        const setScreenSecurityEnabled = vi.fn(async (enabled) => ({ enabled }));
        window.electron = {
            getPlatform: () => "win32",
            setScreenSecurityEnabled,
            getScreenSecuritySettings: vi.fn(async () => ({ enabled: false })),
        };
        await ElectronUtils.setScreenSecurityEnabled(true);
        expect(setScreenSecurityEnabled).toHaveBeenCalledWith(true);
        await ElectronUtils.setScreenSecurityEnabled("yes");
        expect(setScreenSecurityEnabled).toHaveBeenCalledWith(false);
        await ElectronUtils.setScreenSecurityEnabled(0);
        expect(setScreenSecurityEnabled).toHaveBeenCalledWith(false);
        await ElectronUtils.setScreenSecurityEnabled(null);
        expect(setScreenSecurityEnabled).toHaveBeenCalledWith(false);
    });

    it("tolerates missing optional bridge methods", async () => {
        window.electron = {
            getPlatform: () => "win32",
        };
        expect(ElectronUtils.isWindowsElectron()).toBe(true);
        await expect(ElectronUtils.getScreenSecuritySettings()).resolves.toBeNull();
        await expect(ElectronUtils.setScreenSecurityEnabled(true)).resolves.toBeNull();
    });
});
