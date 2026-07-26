// SPDX-License-Identifier: 0BSD

/**
 * Independent oracles for UI locale and theme invariants.
 * Tests compare product code against these predictions without duplicating implementation details.
 */

import { listLocaleCodes, normalizeUiLocaleCode } from "./localeLoader.js";

/**
 * Expected boot theme after boot-theme.js runs.
 *
 * @param {string | null | undefined} storedTheme from localStorage or Android bridge
 * @returns {{ mode: "light" | "dark", htmlDark: boolean }}
 */
export function bootThemeOracle(storedTheme) {
    const mode = storedTheme === "light" || storedTheme === "dark" ? storedTheme : "dark";
    return {
        mode,
        htmlDark: mode === "dark",
    };
}

/**
 * Expected WebGL clear color for light vs dark (matches networkVisualiserWebGL.js).
 *
 * @param {boolean} dark
 * @returns {{ r: number, g: number, b: number, a: number }}
 */
export function visualiserClearColorOracle(dark) {
    if (dark) {
        return { r: 0.035, g: 0.035, b: 0.04, a: 1 };
    }
    return { r: 0.973, g: 0.98, b: 0.988, a: 1 };
}

/**
 * Expected visualiser dark flag from app config and html fallback.
 *
 * @param {string | null | undefined} configTheme
 * @param {boolean} htmlHasDarkClass
 * @returns {boolean}
 */
export function visualiserIsDarkOracle(configTheme, htmlHasDarkClass) {
    if (configTheme === "light") {
        return false;
    }
    if (configTheme === "dark") {
        return true;
    }
    return Boolean(htmlHasDarkClass);
}

/**
 * UI locale after normalization must always be a bundled pack code.
 *
 * @param {unknown} raw
 * @returns {string}
 */
export function uiLocalePackOracle(raw) {
    const code = normalizeUiLocaleCode(raw);
    const packs = listLocaleCodes();
    if (!packs.includes(code)) {
        throw new Error(`oracle violation: normalized locale ${code} not in packs`);
    }
    return code;
}

/**
 * Reticulum manual doc language codes must not be written to UI config.language.
 *
 * @param {string} docLang
 * @returns {boolean} true when docLang would corrupt UI locale if stored as config.language
 */
export function docLangCorruptsUiLocale(docLang) {
    const normalized = normalizeUiLocaleCode(docLang);
    const packs = listLocaleCodes();
    return !packs.includes(docLang) && packs.includes(normalized) && normalized !== docLang;
}
