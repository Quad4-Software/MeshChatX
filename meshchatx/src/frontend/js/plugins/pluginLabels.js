// SPDX-License-Identifier: 0BSD

import en from "../../locales/en.json";

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
 * @param {Record<string, unknown>} messages
 * @param {string} [prefix]
 * @returns {string[]}
 */
function collectLocaleKeys(messages, prefix = "") {
    /** @type {string[]} */
    const keys = [];
    if (!messages || typeof messages !== "object") {
        return keys;
    }
    for (const [key, value] of Object.entries(messages)) {
        if (key.startsWith("_")) {
            continue;
        }
        const path = prefix ? `${prefix}.${key}` : key;
        if (typeof value === "string") {
            keys.push(path);
        } else if (value && typeof value === "object" && !Array.isArray(value)) {
            keys.push(...collectLocaleKeys(value, path));
        }
    }
    return keys;
}

/**
 * @param {(key: string) => string} translate
 * @returns {Record<string, string>}
 */
export function buildPluginLabelMap(translate) {
    /** @type {Record<string, string>} */
    const labels = {};
    const keys = collectLocaleKeys(en.plugins || {}, "plugins");
    for (const key of keys) {
        const value = translate(key);
        if (typeof value === "string" && value !== key) {
            labels[key] = value;
        }
    }
    return labels;
}
