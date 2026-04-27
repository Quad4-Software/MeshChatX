// SPDX-License-Identifier: 0BSD AND MIT

import { describe, it, expect } from "vitest";
import {
    foldForSearch,
    matchesSettingSearch,
    normalizeSearchString,
    tokenizeSettingsQuery,
} from "../../meshchatx/src/frontend/js/settingsSearchUtils.js";

const t = (key) => {
    const map = {
        "app.theme": "Theme",
        "app.dark_theme": "Dark mode",
        "app.stranger_protection": "Stranger protection",
    };
    return map[key] ?? key;
};

describe("settingsSearchUtils", () => {
    it("normalizeSearchString trims and strips zero-width", () => {
        expect(normalizeSearchString("  foo\u200b ")).toBe("foo");
        expect(normalizeSearchString("\uFEFF")).toBe("");
    });

    it("tokenizeSettingsQuery splits on whitespace", () => {
        expect(tokenizeSettingsQuery("dark theme")).toEqual(["dark", "theme"]);
    });

    it("foldForSearch removes combining marks", () => {
        expect(foldForSearch("Café")).toBe("cafe");
    });

    it("matchesSettingSearch: empty query matches", () => {
        expect(matchesSettingSearch(["app.theme"], t, "")).toBe(true);
        expect(matchesSettingSearch(["app.theme"], t, "   ")).toBe(true);
    });

    it("matchesSettingSearch: single token substring", () => {
        expect(matchesSettingSearch(["app.theme", "app.dark_theme"], t, "dark")).toBe(true);
        expect(matchesSettingSearch(["app.theme"], t, "zzz")).toBe(false);
    });

    it("matchesSettingSearch: all tokens must match (AND)", () => {
        expect(matchesSettingSearch(["app.stranger_protection", "block"], t, "stranger block")).toBe(true);
        expect(matchesSettingSearch(["app.stranger_protection"], t, "stranger block")).toBe(false);
    });

    it("matchesSettingSearch: resolves i18n keys with dots", () => {
        expect(matchesSettingSearch(["app.theme"], t, "Theme")).toBe(true);
    });
});
