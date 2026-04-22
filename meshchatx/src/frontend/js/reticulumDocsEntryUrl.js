/**
 * Locales that ship a localized root index (index_<locale>.html) in the
 * Reticulum website bundle. The Sphinx manual itself is English-only under
 * manual/; other locales use these pages like the public site.
 */
const BUNDLED_RETICULUM_SITE_INDEX_LOCALES = new Set(["de", "es", "jp", "nl", "pl", "pt-br", "tr", "uk", "zh-cn"]);

/**
 * @param {string | undefined} locale
 * @returns {string} path relative to /reticulum-docs/ (no leading slash)
 */
export function bundledReticulumDocsEntryPath(locale) {
    const lang = (locale || "en").toLowerCase();
    if (lang === "en") {
        return "manual/index.html";
    }
    if (BUNDLED_RETICULUM_SITE_INDEX_LOCALES.has(lang)) {
        return `index_${lang}.html`;
    }
    return "manual/index.html";
}

/**
 * @param {string | undefined} locale
 * @returns {string} absolute app path for the default bundled Reticulum docs view
 */
export function bundledReticulumDocsUrl(locale) {
    return `/reticulum-docs/${bundledReticulumDocsEntryPath(locale)}`;
}
