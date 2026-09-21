// SPDX-License-Identifier: 0BSD

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { resolveVisualiserIsDark } from "../../meshchatx/src/frontend/features/network-visualiser/lib/visualiserPrefs.js";
import GlobalState from "../../meshchatx/src/frontend/js/GlobalState";
import {
    expectedBootTheme,
    docLangCorruptsUiLocale,
    expectedUiLocalePack,
    expectedVisualiserClearColor,
    expectedVisualiserIsDark,
} from "../../meshchatx/src/frontend/js/localeThemeExpectations.js";
import { normalizeUiLocaleCode, listLocaleCodes } from "../../meshchatx/src/frontend/js/localeLoader.js";

const ROOT = resolve(import.meta.dirname, "../..");
const BOOT_THEME_JS = resolve(ROOT, "meshchatx/src/frontend/public/boot-theme.js");

function runBootTheme(storedTheme, androidTheme = null) {
    document.documentElement.className = "";
    delete document.documentElement.dataset.bootTheme;
    document.documentElement.style.colorScheme = "";
    window.localStorage.clear();
    delete window.MeshChatXAndroid;
    if (storedTheme != null) {
        window.localStorage.setItem("meshchatx_ui_theme", storedTheme);
    }
    if (androidTheme != null) {
        window.MeshChatXAndroid = { getPreferredUiTheme: () => androidTheme };
    }
    const code = readFileSync(BOOT_THEME_JS, "utf8");
    // eslint-disable-next-line no-new-func
    Function(code)();
}

describe("localeTheme oracles", () => {
    describe("expectedBootTheme vs boot-theme.js", () => {
        beforeEach(() => {
            document.documentElement.className = "";
            window.localStorage.clear();
            delete window.MeshChatXAndroid;
        });

        afterEach(() => {
            document.documentElement.className = "";
            window.localStorage.clear();
            delete window.MeshChatXAndroid;
        });

        it.each([
            [null, "light"],
            ["", "light"],
            ["bogus", "light"],
            ["light", "light"],
            ["dark", "dark"],
        ])("stored %j resolves to mode %s", (stored, expectedMode) => {
            const oracle = expectedBootTheme(stored);
            expect(oracle.mode).toBe(expectedMode);
            runBootTheme(stored);
            expect(document.documentElement.dataset.bootTheme).toBe(expectedMode);
            expect(document.documentElement.classList.contains("dark")).toBe(oracle.htmlDark);
        });

        it("system theme follows prefers-color-scheme oracle", () => {
            Object.defineProperty(window, "matchMedia", {
                writable: true,
                value: (query) => ({
                    matches: query.includes("dark"),
                    addEventListener: () => {},
                    removeEventListener: () => {},
                }),
            });
            const oracle = expectedBootTheme("system", true);
            expect(oracle.mode).toBe("dark");
            runBootTheme("system");
            expect(document.documentElement.dataset.bootTheme).toBe("dark");
        });

        it("light oracle requires html.dark removed even when pre-seeded", () => {
            document.documentElement.classList.add("dark");
            const oracle = expectedBootTheme("light");
            expect(oracle.htmlDark).toBe(false);
            runBootTheme("light");
            expect(document.documentElement.classList.contains("dark")).toBe(false);
        });
    });

    describe("expectedVisualiserIsDark vs resolveVisualiserIsDark", () => {
        afterEach(() => {
            GlobalState.config = {};
            document.documentElement.classList.remove("dark");
        });

        it.each([
            ["light", true, false],
            ["light", false, false],
            ["dark", false, true],
            [undefined, true, true],
            [undefined, false, false],
            ["", true, true],
        ])("config.theme=%j html.dark=%s => %s", (theme, htmlDark, expected) => {
            GlobalState.config = theme === undefined ? {} : { theme };
            if (htmlDark) {
                document.documentElement.classList.add("dark");
            } else {
                document.documentElement.classList.remove("dark");
            }
            expect(expectedVisualiserIsDark(theme, htmlDark)).toBe(expected);
            expect(resolveVisualiserIsDark()).toBe(expected);
        });
    });

    describe("expectedVisualiserClearColor", () => {
        it("light and dark are distinct and opaque", () => {
            const light = expectedVisualiserClearColor(false);
            const dark = expectedVisualiserClearColor(true);
            expect(light.a).toBe(1);
            expect(dark.a).toBe(1);
            expect(light.r).toBeGreaterThan(dark.r);
        });
    });

    describe("expectedUiLocalePack", () => {
        it("maps Reticulum manual codes that would break UI packs", () => {
            expect(docLangCorruptsUiLocale("jp")).toBe(true);
            expect(docLangCorruptsUiLocale("zh-cn")).toBe(true);
            expect(docLangCorruptsUiLocale("ru")).toBe(false);
            expect(expectedUiLocalePack("zh-cn")).toBe("zh");
            expect(expectedUiLocalePack("ru")).toBe("ru");
        });

        it("every bundled pack normalizes to itself", () => {
            for (const code of listLocaleCodes()) {
                expect(expectedUiLocalePack(code)).toBe(code);
                expect(normalizeUiLocaleCode(code.toUpperCase())).toBe(code);
            }
        });
    });
});
