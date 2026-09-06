// SPDX-License-Identifier: 0BSD

/**
 * Independent oracles for UI locale and theme invariants.
 * Tests compare product code against these predictions without duplicating implementation details.
 */

import { listLocaleCodes, normalizeUiLocaleCode } from "./localeLoader.js";

export type BootThemeOracleResult = {
    mode: "light" | "dark";
    htmlDark: boolean;
};

export type RgbaColor = {
    r: number;
    g: number;
    b: number;
    a: number;
};

/** Expected boot theme after boot-theme.js runs. */
export function bootThemeOracle(storedTheme: string | null | undefined, prefersDark = false): BootThemeOracleResult {
    if (storedTheme === "system") {
        const mode = prefersDark ? "dark" : "light";
        return {
            mode,
            htmlDark: mode === "dark",
        };
    }
    const mode = storedTheme === "dark" ? "dark" : "light";
    return {
        mode,
        htmlDark: mode === "dark",
    };
}

/** Expected WebGL clear color for light vs dark (matches networkVisualiserWebGL.js). */
export function visualiserClearColorOracle(dark: boolean): RgbaColor {
    if (dark) {
        return { r: 0.035, g: 0.035, b: 0.04, a: 1 };
    }
    return { r: 0.973, g: 0.98, b: 0.988, a: 1 };
}

/** Expected visualiser dark flag from app config and html fallback. */
export function visualiserIsDarkOracle(configTheme: string | null | undefined, htmlHasDarkClass: boolean): boolean {
    if (configTheme === "light") {
        return false;
    }
    if (configTheme === "dark") {
        return true;
    }
    return Boolean(htmlHasDarkClass);
}

/** UI locale after normalization must always be a bundled pack code. */
export function uiLocalePackOracle(raw: unknown): string {
    const code = normalizeUiLocaleCode(raw);
    const packs = listLocaleCodes();
    if (!packs.includes(code)) {
        throw new Error(`oracle violation: normalized locale ${code} not in packs`);
    }
    return code;
}

/**
 * Reticulum manual doc language codes must not be written to UI config.language.
 * Returns true when docLang would corrupt UI locale if stored as config.language.
 */
export function docLangCorruptsUiLocale(docLang: string): boolean {
    const normalized = normalizeUiLocaleCode(docLang);
    const packs = listLocaleCodes();
    return !packs.includes(docLang) && packs.includes(normalized) && normalized !== docLang;
}
