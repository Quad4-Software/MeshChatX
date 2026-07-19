// SPDX-License-Identifier: 0BSD

const localeModules = import.meta.glob("../locales/*.json");

function resolveComposer(i18nOrComposer) {
    if (!i18nOrComposer) {
        return null;
    }
    return i18nOrComposer.global || i18nOrComposer;
}

/**
 * Locale codes discovered from bundled JSON without loading message bodies.
 * @returns {string[]}
 */
export function listLocaleCodes() {
    return Object.keys(localeModules)
        .map((filePath) => {
            const match = filePath.match(/\/([^/]+)\.json$/);
            return match ? match[1] : null;
        })
        .filter(Boolean)
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
    if (composer.availableLocales?.includes(code)) {
        return true;
    }
    if (typeof composer.setLocaleMessage !== "function") {
        return false;
    }
    const loader = localeModules[`../locales/${code}.json`];
    if (!loader) {
        return false;
    }
    const mod = await loader();
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
    const ok = await ensureLocaleMessages(i18nOrComposer, code);
    if (!ok) {
        return false;
    }
    const composer = resolveComposer(i18nOrComposer);
    if (!composer) {
        return false;
    }
    if (composer.locale && typeof composer.locale === "object" && "value" in composer.locale) {
        composer.locale.value = code;
    } else {
        composer.locale = code;
    }
    return true;
}
