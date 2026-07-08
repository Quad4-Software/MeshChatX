// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import en from "../../meshchatx/src/frontend/locales/en.json";
import {
    ALL_SETTINGS_SECTIONS,
    DEFAULT_SETTINGS_TAB,
    getSettingsTab,
    normalizeSettingsTabId,
    SETTINGS_TABS,
    settingsSectionBelongsToTab,
    settingsTabForSection,
} from "../../meshchatx/src/frontend/js/settings/settingsTabs.js";

const KNOWN_SECTIONS_FROM_SETTINGS_PAGE = [
    "strangerProtection",
    "banishment",
    "stickers",
    "gifs",
    "maintenance",
    "plugins",
    "telephony",
    "desktop",
    "android",
    "archiver",
    "nomadRenderer",
    "crawler",
    "appearance",
    "visualiser",
    "location",
    "language",
    "networkSecurity",
    "transport",
    "interfaces",
    "blocked",
    "privacyData",
    "auth",
    "webExposure",
    "infrastructure",
    "csp",
    "messages",
    "notificationSounds",
    "propagation",
    "shortcuts",
];

describe("settingsTabs", () => {
    it("defaults to general tab", () => {
        expect(DEFAULT_SETTINGS_TAB).toBe("general");
        expect(normalizeSettingsTabId(undefined)).toBe("general");
        expect(normalizeSettingsTabId(null)).toBe("general");
        expect(normalizeSettingsTabId("")).toBe("general");
        expect(normalizeSettingsTabId("   ")).toBe("general");
        expect(normalizeSettingsTabId("invalid")).toBe("general");
    });

    it("normalizes valid tab ids and trims whitespace", () => {
        expect(normalizeSettingsTabId("privacy")).toBe("privacy");
        expect(normalizeSettingsTabId("  privacy  ")).toBe("privacy");
    });

    it("rejects case-mismatched tab ids", () => {
        expect(normalizeSettingsTabId("General")).toBe("general");
        expect(normalizeSettingsTabId("PRIVACY")).toBe("general");
    });

    it("maps sections to tabs", () => {
        expect(settingsTabForSection("appearance")).toBe("general");
        expect(settingsTabForSection("messages")).toBe("messages");
        expect(settingsTabForSection("archiver")).toBe("nomad");
        expect(settingsTabForSection("unknown-section")).toBeNull();
    });

    it("includes every section exactly once", () => {
        const seen = SETTINGS_TABS.flatMap((tab) => tab.sections);
        expect(new Set(seen).size).toBe(seen.length);
        expect(seen).toContain("language");
        expect(seen).toContain("networkSecurity");
        expect(seen).toContain("maintenance");
    });

    it("exports ALL_SETTINGS_SECTIONS matching flattened tab sections", () => {
        expect(ALL_SETTINGS_SECTIONS).toEqual(SETTINGS_TABS.flatMap((tab) => tab.sections));
        expect(Object.isFrozen(ALL_SETTINGS_SECTIONS)).toBe(true);
    });

    it("uses unique tab ids and non-empty labels", () => {
        const ids = SETTINGS_TABS.map((tab) => tab.id);
        expect(new Set(ids).size).toBe(ids.length);
        for (const tab of SETTINGS_TABS) {
            expect(tab.labelKey.length).toBeGreaterThan(0);
            expect(tab.descriptionKey.length).toBeGreaterThan(0);
            expect(tab.sections.length).toBeGreaterThan(0);
        }
    });

    it("covers every SettingsPage section key", () => {
        for (const sectionKey of KNOWN_SECTIONS_FROM_SETTINGS_PAGE) {
            expect(ALL_SETTINGS_SECTIONS).toContain(sectionKey);
            expect(settingsTabForSection(sectionKey)).not.toBeNull();
        }
    });

    it("round-trips section to tab membership", () => {
        for (const sectionKey of ALL_SETTINGS_SECTIONS) {
            const tabId = settingsTabForSection(sectionKey);
            expect(tabId).not.toBeNull();
            expect(settingsSectionBelongsToTab(sectionKey, tabId)).toBe(true);
            for (const otherTab of SETTINGS_TABS) {
                if (otherTab.id === tabId) {
                    continue;
                }
                expect(settingsSectionBelongsToTab(sectionKey, otherTab.id)).toBe(false);
            }
        }
    });

    it("getSettingsTab returns tab metadata or null", () => {
        expect(getSettingsTab("network")?.id).toBe("network");
        expect(getSettingsTab("missing")).toBeNull();
        expect(getSettingsTab("")).toBeNull();
    });

    it("uses i18n keys that exist in en.json", () => {
        for (const tab of SETTINGS_TABS) {
            const labelTail = tab.labelKey.replace("settings.tabs.", "");
            const descTail = tab.descriptionKey.replace("settings.tabs.", "");
            expect(en.settings.tabs[labelTail]).toBeTruthy();
            expect(en.settings.tabs[descTail]).toBeTruthy();
        }
    });
});
