// SPDX-License-Identifier: 0BSD

const localeModules = import.meta.glob("../locales/*.json");

/**
 * Real vue-i18n Composer registered at app boot.
 * Options API this.$i18n under legacy:false is a locale-only proxy without
 * setLocaleMessage. Call sites pass that proxy, so loaders must fall back here.
 * @type {import("vue-i18n").Composer | null}
 */
let registeredComposer = null;

/**
 * @param {unknown} obj
 * @returns {boolean}
 */
function hasLocaleMessageApi(obj) {
    return Boolean(obj && typeof obj.setLocaleMessage === "function");
}

/**
 * @param {unknown} composer
 * @returns {string[]}
 */
function listAvailableLocales(composer) {
    const raw = composer?.availableLocales;
    if (Array.isArray(raw)) {
        return raw;
    }
    if (raw && typeof raw === "object" && Array.isArray(raw.value)) {
        return raw.value;
    }
    return [];
}

/**
 * @param {import("vue-i18n").I18n | import("vue-i18n").Composer | null | undefined} i18nOrComposer
 * @returns {import("vue-i18n").Composer | null}
 */
function resolveComposer(i18nOrComposer) {
    if (i18nOrComposer) {
        if (hasLocaleMessageApi(i18nOrComposer.global)) {
            return i18nOrComposer.global;
        }
        if (hasLocaleMessageApi(i18nOrComposer)) {
            return i18nOrComposer;
        }
    }
    if (hasLocaleMessageApi(registeredComposer)) {
        return registeredComposer;
    }
    return null;
}

/**
 * Register the app i18n instance so Options API this.$i18n proxies can load packs.
 * @param {import("vue-i18n").I18n | import("vue-i18n").Composer | null | undefined} i18nOrComposer
 */
export function registerUiI18n(i18nOrComposer) {
    if (!i18nOrComposer) {
        registeredComposer = null;
        return;
    }
    if (hasLocaleMessageApi(i18nOrComposer.global)) {
        registeredComposer = i18nOrComposer.global;
        return;
    }
    if (hasLocaleMessageApi(i18nOrComposer)) {
        registeredComposer = i18nOrComposer;
        return;
    }
    registeredComposer = null;
}

/**
 * Locale codes discovered from bundled JSON without loading message bodies.
 * @returns {string[]}
 */
export function listLocaleCodes(): string[] {
    return Object.keys(localeModules)
        .map((filePath) => {
            const match = filePath.match(/\/([^/]+)\.json$/);
            return match ? match[1] : null;
        })
        .filter((code): code is string => Boolean(code))
        .sort((a, b) => {
            if (a === "en") {
                return -1;
            }
            if (b === "en") {
                return 1;
            }
            return a.localeCompare(b);
        });
}

const UI_LOCALE_ALIASES: any = {
    "zh-cn": "zh",
    zh_cn: "zh",
};

/**
 * Map stored or legacy locale codes to a bundled UI pack code.
 * @param {string | null | undefined} code
 * @returns {string}
 */
export function normalizeUiLocaleCode(code) {
    if (!code || typeof code !== "string") {
        return "en";
    }
    const trimmed = code.trim();
    if (!trimmed) {
        return "en";
    }
    const lower = trimmed.toLowerCase();
    const hyphen = lower.replace(/_/g, "-");
    const aliased = UI_LOCALE_ALIASES[hyphen] || UI_LOCALE_ALIASES[lower];
    if (aliased) {
        return aliased;
    }
    const available = listLocaleCodes();
    if (available.includes(trimmed)) {
        return trimmed;
    }
    if (available.includes(lower)) {
        return lower;
    }
    const base = hyphen.split("-")[0];
    if (available.includes(base)) {
        return base;
    }
    return "en";
}

/**
 * Load a locale message pack into vue-i18n when missing.
 * @param {import("vue-i18n").I18n | import("vue-i18n").Composer} i18nOrComposer
 * @param {string} code
 * @returns {Promise<boolean>}
 */
export async function ensureLocaleMessages(i18nOrComposer, code) {
    if (!code || typeof code !== "string") {
        return false;
    }
    const composer = resolveComposer(i18nOrComposer);
    if (!composer) {
        return false;
    }
    if (listAvailableLocales(composer).includes(code)) {
        return true;
    }
    if (typeof composer.setLocaleMessage !== "function") {
        return false;
    }
    const loader = localeModules[`../locales/${code}.json`];
    if (!loader) {
        return false;
    }
    const mod = (await loader()) as { default?: unknown };
    composer.setLocaleMessage(code, mod.default || mod);
    return true;
}

/**
 * Apply a locale after ensuring its messages are loaded.
 * @param {import("vue-i18n").I18n | import("vue-i18n").Composer} i18nOrComposer
 * @param {string} code
 * @returns {Promise<boolean>}
 */
export async function setLocale(i18nOrComposer, code) {
    const normalized = normalizeUiLocaleCode(code);
    const ok = await ensureLocaleMessages(i18nOrComposer, normalized);
    if (!ok) {
        return false;
    }
    const composer = resolveComposer(i18nOrComposer);
    if (!composer) {
        return false;
    }
    if (composer.locale && typeof composer.locale === "object" && "value" in composer.locale) {
        composer.locale.value = normalized;
    } else {
        composer.locale = normalized;
    }
    if (typeof document !== "undefined") {
        document.documentElement.lang = normalized;
    }
    return true;
}
