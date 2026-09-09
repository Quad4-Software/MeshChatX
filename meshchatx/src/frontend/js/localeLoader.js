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
 * Cached map from canonical BCP 47 locale code to the on-disk JSON file stem.
 * @type {Map<string, string> | null}
 */
let canonicalToStem = null;

/**
 * Cached list of locale options for pickers.
 * @type {Array<{code: string, name: string}> | null}
 */
let localeOptionsCache = null;

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
 * Build the index that maps canonical BCP 47 locale codes to the bundled JSON
 * file stems. File names are canonicalized so the rest of the app uses BCP 47.
 */
function buildFileIndex() {
    if (canonicalToStem) {
        return;
    }
    canonicalToStem = new Map();
    for (const filePath of Object.keys(localeModules)) {
        const match = filePath.match(/\/([^/]+)\.json$/);
        if (!match) {
            continue;
        }
        const stem = match[1];
        const code = canonicalizeBcp47Locale(stem);
        if (code) {
            canonicalToStem.set(code, stem);
        }
    }
}

/**
 * Convert an arbitrary locale string to its canonical BCP 47 form.
 * This never throws; malformed input falls back to a best-effort normalization.
 *
 * @param {string} code
 * @returns {string}
 */
export function canonicalizeBcp47Locale(code) {
    if (typeof code !== "string" || !code) {
        return "";
    }
    const trimmed = code.trim().replace(/_/g, "-");
    if (!trimmed) {
        return "";
    }
    if (typeof Intl !== "undefined" && typeof Intl.getCanonicalLocales === "function") {
        try {
            return Intl.getCanonicalLocales(trimmed)[0] || "";
        } catch {
            // Fall through to best-effort parsing.
        }
    }
    const parts = trimmed.split("-");
    if (parts.length === 0) {
        return "";
    }
    return parts
        .map((part, index) => {
            if (index === 0) {
                return part.toLowerCase();
            }
            if (/^[a-zA-Z]{4}$/.test(part)) {
                return part.slice(0, 1).toUpperCase() + part.slice(1).toLowerCase();
            }
            if (/^[a-zA-Z]{2}$/.test(part) || /^\d{3}$/.test(part)) {
                return part.toUpperCase();
            }
            return part.toLowerCase();
        })
        .join("-");
}

/**
 * Get the native name for a BCP 47 language tag using the platform
 * Intl.DisplayNames API. Falls back to the tag itself if unavailable.
 *
 * @param {string} code
 * @returns {string}
 */
function getNativeLanguageName(code) {
    if (typeof Intl === "undefined" || typeof Intl.DisplayNames !== "function") {
        return code;
    }
    try {
        const rawName = new Intl.DisplayNames(code, { type: "language" }).of(code);
        if (typeof rawName !== "string") {
            return code;
        }
        return rawName.replace(/^\p{LC}/u, (ch) => ch.toUpperCase());
    } catch {
        return code;
    }
}

/**
 * Locale codes discovered from bundled JSON without loading message bodies.
 * @returns {string[]}
 */
export function listLocaleCodes() {
    buildFileIndex();
    return Array.from(canonicalToStem.keys()).sort((a, b) => {
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
 * Return all bundled UI locales with native names for pickers.
 * English is pinned first; the remaining entries are sorted by native name.
 *
 * @returns {Array<{code: string, name: string}>}
 */
export function listLocaleOptions() {
    if (localeOptionsCache) {
        return localeOptionsCache;
    }
    const codes = listLocaleCodes();
    const options = codes.map((code) => ({
        code,
        name: getNativeLanguageName(code),
    }));
    options.sort((a, b) => {
        if (a.code === "en") {
            return -1;
        }
        if (b.code === "en") {
            return 1;
        }
        return a.name.localeCompare(b.name);
    });
    localeOptionsCache = options;
    return localeOptionsCache;
}

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
    buildFileIndex();
    const canonical = canonicalizeBcp47Locale(trimmed);
    if (canonicalToStem.has(canonical)) {
        return canonical;
    }
    const parts = canonical.split("-");
    while (parts.length > 1) {
        parts.pop();
        const base = parts.join("-");
        if (canonicalToStem.has(base)) {
            return base;
        }
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
    buildFileIndex();
    const canonical = canonicalizeBcp47Locale(code.trim());
    const stem = canonicalToStem.get(canonical);
    if (!stem) {
        return false;
    }
    const composer = resolveComposer(i18nOrComposer);
    if (!composer) {
        return false;
    }
    if (listAvailableLocales(composer).includes(canonical)) {
        return true;
    }
    if (typeof composer.setLocaleMessage !== "function") {
        return false;
    }
    const loader = localeModules[`../locales/${stem}.json`];
    if (!loader) {
        return false;
    }
    const mod = await loader();
    composer.setLocaleMessage(canonical, mod.default || mod);
    return true;
}

/**
 * Apply a locale after ensuring its messages are loaded.
 * @param {import("vue-i18n").I18n | import("vue-i18n").Composer} i18nOrComposer
 * @param {string} code
 * @returns {Promise<boolean>}
 */
export async function setLocale(i18nOrComposer, code) {
    const canonical = normalizeUiLocaleCode(code);
    const ok = await ensureLocaleMessages(i18nOrComposer, canonical);
    if (!ok) {
        return false;
    }
    const composer = resolveComposer(i18nOrComposer);
    if (!composer) {
        return false;
    }
    if (composer.locale && typeof composer.locale === "object" && "value" in composer.locale) {
        composer.locale.value = canonical;
    } else {
        composer.locale = canonical;
    }
    if (typeof document !== "undefined") {
        document.documentElement.lang = canonical;
    }
    return true;
}
