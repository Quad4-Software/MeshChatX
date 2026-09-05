// SPDX-License-Identifier: 0BSD

import { describe, it, expect } from "vitest";
import {
    buildSettingsSearchHaystack,
    camelCaseToSearchWords,
    foldForSearch,
    matchesSettingSearch,
    normalizeSearchString,
    tokenizeSettingsQuery,
    tokenMatchesHaystack,
} from "../../meshchatx/src/frontend/js/settingsSearchUtils.js";

const t = (key) => {
    const map = {
        "app.theme": "Theme",
        "app.dark_theme": "Dark mode",
        "app.stranger_protection": "Stranger protection",
        "settings.tabs.network": "Network",
        "settings.tabs.privacy": "Privacy",
    };
    return map[key] ?? key;
};

describe("settingsSearchUtils", () => {
    it("normalizeSearchString trims and strips zero-width", () => {
        expect(normalizeSearchString("  foo\u200b ")).toBe("foo");
        expect(normalizeSearchString("\uFEFF")).toBe("");
    });

    it("tokenizeSettingsQuery splits on whitespace and punctuation", () => {
        expect(tokenizeSettingsQuery("dark theme")).toEqual(["dark", "theme"]);
        expect(tokenizeSettingsQuery("dark-mode")).toEqual(["dark", "mode"]);
        expect(tokenizeSettingsQuery("content_security/policy")).toEqual(["content", "security", "policy"]);
        expect(tokenizeSettingsQuery("index.mu")).toEqual(["index", "mu"]);
    });

    it("foldForSearch removes combining marks", () => {
        expect(foldForSearch("Café")).toBe("cafe");
    });

    it("camelCaseToSearchWords splits section ids", () => {
        expect(camelCaseToSearchWords("strangerProtection")).toBe("stranger protection");
        expect(camelCaseToSearchWords("networkSecurity")).toBe("network security");
        expect(camelCaseToSearchWords("nomadRenderer")).toBe("nomad renderer");
    });

    it("tokenMatchesHaystack: short tokens are whole words", () => {
        expect(tokenMatchesHaystack("me", "theme dark mode", "themedarkmode")).toBe(false);
        expect(tokenMatchesHaystack("me", "messages mesh", "messagesmesh")).toBe(false);
        expect(tokenMatchesHaystack("me", "me myself", "memyself")).toBe(true);
        expect(tokenMatchesHaystack("fi", "suomi finnish fi locale", "suomifinnishfilocale")).toBe(true);
        expect(tokenMatchesHaystack("fi", "firewall allowlist", "firewallallowlist")).toBe(false);
    });

    it("tokenMatchesHaystack: long tokens match compact haystack", () => {
        expect(tokenMatchesHaystack("darkmode", "dark mode theme", "darkmodetheme")).toBe(true);
        expect(tokenMatchesHaystack("zzz", "dark mode", "darkmode")).toBe(false);
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

    it("matchesSettingSearch: hyphenated query matches spaced haystack", () => {
        expect(matchesSettingSearch(["app.dark_theme"], t, "dark-mode")).toBe(true);
        expect(matchesSettingSearch(["app.dark_theme"], t, "darkmode")).toBe(true);
    });

    it("matchesSettingSearch: resolves i18n keys with dots", () => {
        expect(matchesSettingSearch(["app.theme"], t, "Theme")).toBe(true);
    });

    it("matchesSettingSearch: treats = prefix as literal text", () => {
        expect(matchesSettingSearch(["=index.mu"], t, "index.mu")).toBe(true);
        expect(matchesSettingSearch(["=index.html"], t, "html")).toBe(true);
    });

    it("matchesSettingSearch: tab labels in extras", () => {
        expect(matchesSettingSearch(["settings.tabs.network"], t, "network")).toBe(true);
        expect(matchesSettingSearch(["=stranger protection"], t, "stranger")).toBe(true);
    });

    it("buildSettingsSearchHaystack folds translated snippets", () => {
        const { haystack, compactHaystack } = buildSettingsSearchHaystack(["app.dark_theme"], t);
        expect(haystack).toBe("dark mode");
        expect(compactHaystack).toBe("darkmode");
    });

    it("buildSettingsSearchHaystack splits punctuation so index.mu tokens match", () => {
        const { haystack } = buildSettingsSearchHaystack(["=index.mu"], t);
        expect(haystack).toBe("index mu");
    });
});
