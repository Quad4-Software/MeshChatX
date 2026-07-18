// SPDX-License-Identifier: 0BSD

const fs = require("fs");
const path = require("node:path");

function defaultDesktopPrivacySettings() {
    return {
        screenSecurityEnabled: false,
    };
}

function desktopPrivacySettingsPath(storageDir) {
    return path.join(storageDir, "desktop-privacy-settings.json");
}

function normalizeDesktopPrivacySettings(raw) {
    const defaults = defaultDesktopPrivacySettings();
    if (!raw || typeof raw !== "object") {
        return defaults;
    }
    return {
        screenSecurityEnabled:
            typeof raw.screenSecurityEnabled === "boolean" ? raw.screenSecurityEnabled : defaults.screenSecurityEnabled,
    };
}

function loadDesktopPrivacySettings(storageDir) {
    try {
        const filePath = desktopPrivacySettingsPath(storageDir);
        if (!fs.existsSync(filePath)) {
            return defaultDesktopPrivacySettings();
        }
        const parsed = JSON.parse(fs.readFileSync(filePath, "utf8"));
        return normalizeDesktopPrivacySettings(parsed);
    } catch {
        return defaultDesktopPrivacySettings();
    }
}

function saveDesktopPrivacySettings(storageDir, partial) {
    const current = loadDesktopPrivacySettings(storageDir);
    const next = normalizeDesktopPrivacySettings({
        ...current,
        ...(partial && typeof partial === "object" ? partial : {}),
    });
    try {
        fs.mkdirSync(storageDir, { recursive: true });
        fs.writeFileSync(desktopPrivacySettingsPath(storageDir), JSON.stringify(next, null, 2), "utf8");
    } catch {
        // ignore persistence failures; in-memory choice still applies for this session
    }
    return next;
}

/**
 * Windows is the primary target (Recall / capture pipelines).
 * Electron also supports content protection on macOS.
 * @param {string} platform
 * @returns {boolean}
 */
function isScreenSecurityPlatformSupported(platform) {
    return platform === "win32" || platform === "darwin";
}

/**
 * Apply content protection to a BrowserWindow-like object.
 * Safe against destroyed windows and missing APIs.
 * @param {{ isDestroyed?: () => boolean, setContentProtection?: (enabled: boolean) => void } | null | undefined} windowLike
 * @param {boolean} enabled
 * @returns {boolean} true when protection was applied
 */
function applyContentProtection(windowLike, enabled) {
    if (!windowLike) {
        return false;
    }
    if (typeof windowLike.isDestroyed === "function" && windowLike.isDestroyed()) {
        return false;
    }
    if (typeof windowLike.setContentProtection !== "function") {
        return false;
    }
    try {
        windowLike.setContentProtection(enabled === true);
        return true;
    } catch {
        return false;
    }
}

/**
 * Apply content protection across a list of windows.
 * @param {Array<{ isDestroyed?: () => boolean, setContentProtection?: (enabled: boolean) => void }>} windows
 * @param {boolean} enabled
 * @returns {number} number of windows updated
 */
function applyContentProtectionToWindows(windows, enabled) {
    if (!Array.isArray(windows)) {
        return 0;
    }
    let applied = 0;
    for (const win of windows) {
        if (applyContentProtection(win, enabled)) {
            applied += 1;
        }
    }
    return applied;
}

module.exports = {
    defaultDesktopPrivacySettings,
    normalizeDesktopPrivacySettings,
    loadDesktopPrivacySettings,
    saveDesktopPrivacySettings,
    isScreenSecurityPlatformSupported,
    desktopPrivacySettingsPath,
    applyContentProtection,
    applyContentProtectionToWindows,
};
