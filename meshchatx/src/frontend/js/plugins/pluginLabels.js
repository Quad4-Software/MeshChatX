// SPDX-License-Identifier: 0BSD

/**
 * Flatten nested locale objects into dotted keys for plugin worker translation.
 *
 * @param {Record<string, unknown>} messages
 * @param {string} [prefix]
 * @returns {Record<string, string>}
 */
export function flattenLocaleMessages(messages, prefix = "") {
    /** @type {Record<string, string>} */
    const flat = {};
    if (!messages || typeof messages !== "object") {
        return flat;
    }
    for (const [key, value] of Object.entries(messages)) {
        if (key.startsWith("_")) {
            continue;
        }
        const path = prefix ? `${prefix}.${key}` : key;
        if (typeof value === "string") {
            flat[path] = value;
        } else if (value && typeof value === "object" && !Array.isArray(value)) {
            Object.assign(flat, flattenLocaleMessages(value, path));
        }
    }
    return flat;
}

/**
 * @param {ReturnType<import('../apiClient.js').createApiClient>} apiClient
 * @param {string} pluginId
 * @param {string} locale
 * @param {Record<string, unknown>} [manifest]
 * @returns {Promise<Record<string, string>>}
 */
export async function loadPluginLabelMap(apiClient, pluginId, locale, manifest = {}) {
    const i18n = manifest.i18n || {};
    const directory = i18n.directory || "locales";
    const defaultLocale = i18n.defaultLocale || "en";
    const candidates = [];
    for (const code of [locale, defaultLocale, "en"]) {
        if (code && !candidates.includes(code)) {
            candidates.push(code);
        }
    }
    for (const code of candidates) {
        try {
            const assetPath = `${directory}/${code}.json`;
            const response = await apiClient.get(
                `/api/v1/plugins/${encodeURIComponent(pluginId)}/asset/${assetPath}`,
                { responseType: "json" }
            );
            if (response.data && typeof response.data === "object") {
                return flattenLocaleMessages(response.data);
            }
        } catch {
            // try next locale candidate
        }
    }
    return {};
}

/**
 * @param {Record<string, string>} labels
 * @param {string} key
 * @param {Record<string, unknown>} [manifest]
 * @returns {string}
 */
export function resolvePluginUiString(labels, key, manifest = {}) {
    if (labels[key]) {
        return labels[key];
    }
    if (key === "title") {
        return typeof manifest.name === "string" ? manifest.name : key;
    }
    if (key === "description") {
        return typeof manifest.description === "string" ? manifest.description : key;
    }
    if (key === "nav") {
        return typeof manifest.name === "string" ? manifest.name : key;
    }
    return key;
}
