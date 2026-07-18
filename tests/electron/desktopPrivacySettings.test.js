// SPDX-License-Identifier: 0BSD

import { createRequire } from "module";
import path from "path";
import fs from "fs";
import os from "os";
import { afterEach, describe, expect, it, vi } from "vitest";

const require = createRequire(import.meta.url);
const {
    defaultDesktopPrivacySettings,
    normalizeDesktopPrivacySettings,
    loadDesktopPrivacySettings,
    saveDesktopPrivacySettings,
    isScreenSecurityPlatformSupported,
    applyContentProtection,
    applyContentProtectionToWindows,
    desktopPrivacySettingsPath,
} = require("../../electron/desktopPrivacySettings.js");

describe("electron/desktopPrivacySettings", () => {
    const tempDirs = [];

    afterEach(() => {
        for (const dir of tempDirs.splice(0)) {
            fs.rmSync(dir, { recursive: true, force: true });
        }
    });

    it("defaults screen security off", () => {
        expect(defaultDesktopPrivacySettings()).toEqual({
            screenSecurityEnabled: false,
        });
    });

    it("normalizes invalid and missing values", () => {
        expect(normalizeDesktopPrivacySettings(null)).toEqual(defaultDesktopPrivacySettings());
        expect(normalizeDesktopPrivacySettings([])).toEqual(defaultDesktopPrivacySettings());
        expect(normalizeDesktopPrivacySettings({ screenSecurityEnabled: "yes" })).toEqual(
            defaultDesktopPrivacySettings()
        );
        expect(normalizeDesktopPrivacySettings({ screenSecurityEnabled: 1 })).toEqual(
            defaultDesktopPrivacySettings()
        );
        expect(normalizeDesktopPrivacySettings({ screenSecurityEnabled: true })).toEqual({
            screenSecurityEnabled: true,
        });
        expect(normalizeDesktopPrivacySettings({ screenSecurityEnabled: false, extra: 1 })).toEqual({
            screenSecurityEnabled: false,
        });
    });

    it("persists and reloads settings from storage dir", () => {
        const dir = fs.mkdtempSync(path.join(os.tmpdir(), "meshchatx-privacy-"));
        tempDirs.push(dir);
        const saved = saveDesktopPrivacySettings(dir, { screenSecurityEnabled: true });
        expect(saved).toEqual({ screenSecurityEnabled: true });
        expect(loadDesktopPrivacySettings(dir)).toEqual({ screenSecurityEnabled: true });
        expect(fs.existsSync(desktopPrivacySettingsPath(dir))).toBe(true);
    });

    it("returns defaults for missing corrupt and empty files", () => {
        const dir = fs.mkdtempSync(path.join(os.tmpdir(), "meshchatx-privacy-"));
        tempDirs.push(dir);
        expect(loadDesktopPrivacySettings(dir)).toEqual(defaultDesktopPrivacySettings());

        fs.writeFileSync(desktopPrivacySettingsPath(dir), "not-json", "utf8");
        expect(loadDesktopPrivacySettings(dir)).toEqual(defaultDesktopPrivacySettings());

        fs.writeFileSync(desktopPrivacySettingsPath(dir), JSON.stringify(["nope"]), "utf8");
        expect(loadDesktopPrivacySettings(dir)).toEqual(defaultDesktopPrivacySettings());

        fs.writeFileSync(desktopPrivacySettingsPath(dir), JSON.stringify({ screenSecurityEnabled: "x" }), "utf8");
        expect(loadDesktopPrivacySettings(dir)).toEqual(defaultDesktopPrivacySettings());
    });

    it("ignores non-object partials and preserves current state", () => {
        const dir = fs.mkdtempSync(path.join(os.tmpdir(), "meshchatx-privacy-"));
        tempDirs.push(dir);
        saveDesktopPrivacySettings(dir, { screenSecurityEnabled: true });
        expect(saveDesktopPrivacySettings(dir, null)).toEqual({ screenSecurityEnabled: true });
        expect(saveDesktopPrivacySettings(dir, "nope")).toEqual({ screenSecurityEnabled: true });
        expect(saveDesktopPrivacySettings(dir, {})).toEqual({ screenSecurityEnabled: true });
    });

    it("last write wins under concurrent save races", () => {
        const dir = fs.mkdtempSync(path.join(os.tmpdir(), "meshchatx-privacy-race-"));
        tempDirs.push(dir);
        const results = [];
        for (let i = 0; i < 20; i += 1) {
            results.push(saveDesktopPrivacySettings(dir, { screenSecurityEnabled: i % 2 === 0 }));
        }
        const final = loadDesktopPrivacySettings(dir);
        expect(results[results.length - 1]).toEqual(final);
        expect(typeof final.screenSecurityEnabled).toBe("boolean");
    });

    it("reports supported platforms", () => {
        expect(isScreenSecurityPlatformSupported("win32")).toBe(true);
        expect(isScreenSecurityPlatformSupported("darwin")).toBe(true);
        expect(isScreenSecurityPlatformSupported("linux")).toBe(false);
        expect(isScreenSecurityPlatformSupported("")).toBe(false);
        expect(isScreenSecurityPlatformSupported(null)).toBe(false);
        expect(isScreenSecurityPlatformSupported(undefined)).toBe(false);
    });

    it("applyContentProtection skips null destroyed and missing APIs", () => {
        expect(applyContentProtection(null, true)).toBe(false);
        expect(applyContentProtection({ isDestroyed: () => true, setContentProtection: vi.fn() }, true)).toBe(false);
        expect(applyContentProtection({ isDestroyed: () => false }, true)).toBe(false);

        const setContentProtection = vi.fn();
        expect(
            applyContentProtection(
                {
                    isDestroyed: () => false,
                    setContentProtection,
                },
                true
            )
        ).toBe(true);
        expect(setContentProtection).toHaveBeenCalledWith(true);

        const throwing = vi.fn(() => {
            throw new Error("boom");
        });
        expect(
            applyContentProtection(
                {
                    isDestroyed: () => false,
                    setContentProtection: throwing,
                },
                false
            )
        ).toBe(false);
    });

    it("applyContentProtectionToWindows counts only successful applies", () => {
        const ok = { isDestroyed: () => false, setContentProtection: vi.fn() };
        const destroyed = { isDestroyed: () => true, setContentProtection: vi.fn() };
        const missing = { isDestroyed: () => false };
        expect(applyContentProtectionToWindows(null, true)).toBe(0);
        expect(applyContentProtectionToWindows([ok, destroyed, missing, null], true)).toBe(1);
        expect(ok.setContentProtection).toHaveBeenCalledWith(true);
        expect(destroyed.setContentProtection).not.toHaveBeenCalled();
    });
});
