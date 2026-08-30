// SPDX-License-Identifier: 0BSD

const fs = require("fs");
const path = require("node:path");

const UI_THEMES = new Set(["light", "dark", "system"]);

function uiThemePath(storageDir) {
    return path.join(storageDir, "desktop-ui-theme.json");
}

function normalizeUiThemePreference(raw) {
    if (typeof raw !== "string") {
        return "system";
    }
    const value = raw.trim().toLowerCase();
    if (UI_THEMES.has(value)) {
        return value;
    }
    return "system";
}

function resolveEffectiveUiTheme(preference, prefersDark) {
    const normalized = normalizeUiThemePreference(preference);
    if (normalized === "light" || normalized === "dark") {
        return normalized;
    }
    return prefersDark ? "dark" : "light";
}

function loadUiThemePreference(storageDir) {
    try {
        const filePath = uiThemePath(storageDir);
        if (!fs.existsSync(filePath)) {
            return "system";
        }
        const parsed = JSON.parse(fs.readFileSync(filePath, "utf8"));
        if (parsed && typeof parsed === "object") {
            if (typeof parsed.preference === "string") {
                return normalizeUiThemePreference(parsed.preference);
            }
            if (typeof parsed.theme === "string") {
                return normalizeUiThemePreference(parsed.theme);
            }
        }
    } catch {
        // ignore corrupt preference files
    }
    return "system";
}

function saveUiThemePreference(storageDir, preference) {
    const next = normalizeUiThemePreference(preference);
    try {
        fs.mkdirSync(storageDir, { recursive: true });
        fs.writeFileSync(uiThemePath(storageDir), JSON.stringify({ preference: next }, null, 2), "utf8");
    } catch {
        // ignore persistence failures
    }
    return next;
}

function shellBackgroundColor(effectiveTheme) {
    return effectiveTheme === "dark" ? "#09090b" : "#f8fafc";
}

module.exports = {
    loadUiThemePreference,
    saveUiThemePreference,
    resolveEffectiveUiTheme,
    normalizeUiThemePreference,
    shellBackgroundColor,
    uiThemePath,
};
