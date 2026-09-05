// SPDX-License-Identifier: 0BSD

/**
 * Framework-free message lookup over vue-i18n composer or a plain dictionary.
 * Svelte pages use t() from here. Vue keeps $t.
 */

/** @type {((key: string, values?: Record<string, unknown>) => string) | null} */
let translateFn = null;

/** @type {Record<string, unknown> | null} */
let fallbackMessages = null;

/**
 * @param {string} key
 * @param {Record<string, unknown>} [messages]
 * @returns {unknown}
 */
function lookupPath(key, messages) {
    if (!messages || typeof messages !== "object") {
        return undefined;
    }
    const parts = String(key).split(".");
    let cur = messages;
    for (const part of parts) {
        if (cur == null || typeof cur !== "object") {
            return undefined;
        }
        cur = cur[part];
    }
    return cur;
}

/**
 * @param {string} template
 * @param {Record<string, unknown>} [values]
 * @returns {string}
 */
function interpolate(template, values) {
    if (!values || typeof values !== "object") {
        return template;
    }
    return template.replace(/\{(\w+)\}/g, (_, name) => {
        if (Object.prototype.hasOwnProperty.call(values, name)) {
            return String(values[name]);
        }
        return `{${name}}`;
    });
}

/**
 * Register the app translator (usually vue-i18n global.t).
 * @param {((key: string, values?: Record<string, unknown>) => string) | null | undefined} fn
 */
export function registerTranslator(fn) {
    translateFn = typeof fn === "function" ? fn : null;
}

/**
 * Optional plain message tree used when no vue-i18n translator is registered (tests / early boot).
 * @param {Record<string, unknown> | null | undefined} messages
 */
export function registerFallbackMessages(messages) {
    fallbackMessages = messages && typeof messages === "object" ? messages : null;
}

/**
 * Translate a key. Returns the key when missing.
 * @param {string} key
 * @param {Record<string, unknown>} [values]
 * @returns {string}
 */
export function t(key, values) {
    if (translateFn) {
        try {
            const out = translateFn(key, values);
            if (out != null && out !== "") {
                return String(out);
            }
        } catch {
            /* fall through */
        }
    }
    const found = lookupPath(key, fallbackMessages);
    if (typeof found === "string") {
        return interpolate(found, values);
    }
    return String(key);
}
