// SPDX-License-Identifier: 0BSD

/**
 * Demo-mode UI preference overlay.
 * Persists cosmetic settings in localStorage when the server rejects
 * PATCH /api/v1/config. Does not store identity material or mesh secrets.
 */

export const DEMO_UI_PREFS_STORAGE_KEY = "meshchatx_demo_ui_prefs";
export const DEMO_UI_LANGUAGE_STORAGE_KEY = "meshchatx_ui_language";

/** Config keys safe to mirror locally in public demo mode. */
export const DEMO_UI_PREF_KEYS = Object.freeze([
    "theme",
    "theme_preset",
    "language",
    "display_name",
    "accent_color",
    "ui_transparency",
    "ui_glass_enabled",
    "message_font_size",
    "message_icon_size",
    "message_outbound_bubble_color",
    "message_inbound_bubble_color",
    "message_failed_bubble_color",
    "message_waiting_bubble_color",
    "banished_effect_enabled",
    "banished_text",
    "banished_color",
    "show_unknown_contact_banner",
    "map_tile_cache_enabled",
    "map_offline_enabled",
    "nomad_render_markdown_enabled",
    "nomad_render_html_enabled",
    "nomad_render_plaintext_enabled",
]);

const DEMO_UI_PREF_KEY_SET = new Set(DEMO_UI_PREF_KEYS);

/**
 * @param {unknown} value
 * @returns {Record<string, unknown>}
 */
export function sanitizeDemoUiPrefs(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
        return {};
    }
    /** @type {Record<string, unknown>} */
    const out: any = {};
    for (const key of DEMO_UI_PREF_KEYS) {
        if (Object.prototype.hasOwnProperty.call(value, key)) {
            out[key] = value[key];
        }
    }
    return out;
}

/**
 * @param {unknown} partial
 * @returns {Record<string, unknown>}
 */
export function pickDemoUiPrefs(partial) {
    return sanitizeDemoUiPrefs(partial);
}

/**
 * @param {unknown} partial
 * @returns {boolean}
 */
export function partialHasDemoUiPrefs(partial) {
    if (!partial || typeof partial !== "object") {
        return false;
    }
    return Object.keys(partial).some((key) => DEMO_UI_PREF_KEY_SET.has(key));
}

/**
 * @param {Storage | null | undefined} storage
 * @returns {Record<string, unknown>}
 */
export function loadDemoUiPrefs(storage = typeof localStorage !== "undefined" ? localStorage : null) {
    if (!storage) {
        return {};
    }
    try {
        const raw = storage.getItem(DEMO_UI_PREFS_STORAGE_KEY);
        if (!raw) {
            return {};
        }
        return sanitizeDemoUiPrefs(JSON.parse(raw));
    } catch {
        return {};
    }
}

/**
 * @param {Record<string, unknown>} prefs
 * @param {Storage | null | undefined} storage
 */
export function saveDemoUiPrefs(prefs, storage = typeof localStorage !== "undefined" ? localStorage : null) {
    if (!storage) {
        return;
    }
    const next = sanitizeDemoUiPrefs(prefs);
    try {
        storage.setItem(DEMO_UI_PREFS_STORAGE_KEY, JSON.stringify(next));
        if (typeof next.language === "string" && next.language) {
            storage.setItem(DEMO_UI_LANGUAGE_STORAGE_KEY, next.language);
        }
        if (typeof next.theme === "string" && next.theme) {
            storage.setItem("meshchatx_ui_theme", next.theme === "system" ? "system" : next.theme);
        }
    } catch {
        // Quota or private mode: ignore.
    }
}

/**
 * Merge a patch into stored demo prefs and persist.
 * @param {unknown} partial
 * @param {Storage | null | undefined} storage
 * @returns {Record<string, unknown>}
 */
export function mergeAndSaveDemoUiPrefs(partial, storage = typeof localStorage !== "undefined" ? localStorage : null) {
    const merged: any = {
        ...loadDemoUiPrefs(storage),
        ...pickDemoUiPrefs(partial),
    };
    saveDemoUiPrefs(merged, storage);
    return merged;
}

/**
 * Overlay stored demo prefs onto a server config object.
 * @param {Record<string, unknown> | null | undefined} config
 * @param {Storage | null | undefined} storage
 * @returns {Record<string, unknown>}
 */
export function mergeConfigWithDemoUiPrefs(
    config,
    storage = typeof localStorage !== "undefined" ? localStorage : null
) {
    const base = config && typeof config === "object" ? { ...config } : {};
    return { ...base, ...loadDemoUiPrefs(storage) };
}

/**
 * @param {unknown} errData
 * @returns {boolean}
 */
export function isDemoReadonlyRejection(errData) {
    if (!errData || typeof errData !== "object") {
        return false;
    }
    return errData.code === "demo_readonly";
}
