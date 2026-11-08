// SPDX-License-Identifier: 0BSD

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import DesktopUtils from "../../meshchatx/src/frontend/js/DesktopUtils.js";

describe("DesktopUtils screen security edge cases", () => {
    afterEach(() => {
        delete window.desktop;
        vi.restoreAllMocks();
    });

    it("returns nulls when electron bridge is missing", async () => {
        expect(DesktopUtils.isDesktop()).toBe(false);
        expect(DesktopUtils.getPlatform()).toBeNull();
        expect(DesktopUtils.isWindowsDesktop()).toBe(false);
        await expect(DesktopUtils.getScreenSecuritySettings()).resolves.toBeNull();
        await expect(DesktopUtils.setScreenSecurityEnabled(true)).resolves.toBeNull();
    });

    it("isWindowsDesktop requires both electron and win32", () => {
        window.desktop = {
            getPlatform: () => "linux",
        };
        expect(DesktopUtils.isWindowsDesktop()).toBe(false);
        window.desktop.getPlatform = () => "win32";
        expect(DesktopUtils.isWindowsDesktop()).toBe(true);
    });

    it("coerces setScreenSecurityEnabled to a strict boolean for the IPC bridge", async () => {
        const setScreenSecurityEnabled = vi.fn(async (enabled) => ({ enabled }));
        window.desktop = {
            getPlatform: () => "win32",
            setScreenSecurityEnabled,
            getScreenSecuritySettings: vi.fn(async () => ({ enabled: false })),
        };
        await DesktopUtils.setScreenSecurityEnabled(true);
        expect(setScreenSecurityEnabled).toHaveBeenCalledWith(true);
        await DesktopUtils.setScreenSecurityEnabled("yes");
        expect(setScreenSecurityEnabled).toHaveBeenCalledWith(false);
        await DesktopUtils.setScreenSecurityEnabled(0);
        expect(setScreenSecurityEnabled).toHaveBeenCalledWith(false);
        await DesktopUtils.setScreenSecurityEnabled(null);
        expect(setScreenSecurityEnabled).toHaveBeenCalledWith(false);
    });

    it("tolerates missing optional bridge methods", async () => {
        window.desktop = {
            getPlatform: () => "win32",
        };
        expect(DesktopUtils.isWindowsDesktop()).toBe(true);
        await expect(DesktopUtils.getScreenSecuritySettings()).resolves.toBeNull();
        await expect(DesktopUtils.setScreenSecurityEnabled(true)).resolves.toBeNull();
    });
});
