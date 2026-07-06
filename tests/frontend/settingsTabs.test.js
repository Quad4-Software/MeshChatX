// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import {
    DEFAULT_SETTINGS_TAB,
    normalizeSettingsTabId,
    SETTINGS_TABS,
    settingsTabForSection,
} from "../../meshchatx/src/frontend/js/settings/settingsTabs.js";

describe("settingsTabs", () => {
    it("defaults to general tab", () => {
        expect(DEFAULT_SETTINGS_TAB).toBe("general");
        expect(normalizeSettingsTabId(undefined)).toBe("general");
        expect(normalizeSettingsTabId("invalid")).toBe("general");
    });

    it("normalizes valid tab ids", () => {
        expect(normalizeSettingsTabId("privacy")).toBe("privacy");
    });

    it("maps sections to tabs", () => {
        expect(settingsTabForSection("appearance")).toBe("general");
        expect(settingsTabForSection("messages")).toBe("messages");
        expect(settingsTabForSection("archiver")).toBe("nomad");
    });

    it("includes every section exactly once", () => {
        const seen = SETTINGS_TABS.flatMap((tab) => tab.sections);
        expect(new Set(seen).size).toBe(seen.length);
        expect(seen).toContain("language");
        expect(seen).toContain("networkSecurity");
        expect(seen).toContain("maintenance");
    });
});
