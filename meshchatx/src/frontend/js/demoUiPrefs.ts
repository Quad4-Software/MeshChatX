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
] as const);

export type DemoUiPrefKey = (typeof DEMO_UI_PREF_KEYS)[number];
export type DemoUiPrefs = Partial<Record<DemoUiPrefKey, unknown>>;

const DEMO_UI_PREF_KEY_SET = new Set<string>(DEMO_UI_PREF_KEYS);

export function sanitizeDemoUiPrefs(value: unknown): DemoUiPrefs {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
        return {};
    }
    const source = value as Record<string, unknown>;
    const out: DemoUiPrefs = {};
    for (const key of DEMO_UI_PREF_KEYS) {
        if (Object.prototype.hasOwnProperty.call(source, key)) {
            out[key] = source[key];
        }
    }
    return out;
}

export function pickDemoUiPrefs(partial: unknown): DemoUiPrefs {
    return sanitizeDemoUiPrefs(partial);
}

export function partialHasDemoUiPrefs(partial: unknown): boolean {
    if (!partial || typeof partial !== "object") {
        return false;
    }
    return Object.keys(partial as Record<string, unknown>).some((key) => DEMO_UI_PREF_KEY_SET.has(key));
}

export function loadDemoUiPrefs(
    storage: Storage | null | undefined = typeof localStorage !== "undefined" ? localStorage : null
): DemoUiPrefs {
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

export function saveDemoUiPrefs(
    prefs: DemoUiPrefs,
    storage: Storage | null | undefined = typeof localStorage !== "undefined" ? localStorage : null
): void {
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

/** Merge a patch into stored demo prefs and persist. */
export function mergeAndSaveDemoUiPrefs(
    partial: unknown,
    storage: Storage | null | undefined = typeof localStorage !== "undefined" ? localStorage : null
): DemoUiPrefs {
    const merged: DemoUiPrefs = {
        ...loadDemoUiPrefs(storage),
        ...pickDemoUiPrefs(partial),
    };
    saveDemoUiPrefs(merged, storage);
    return merged;
}

/** Overlay stored demo prefs onto a server config object. */
export function mergeConfigWithDemoUiPrefs(
    config: Record<string, unknown> | null | undefined,
    storage: Storage | null | undefined = typeof localStorage !== "undefined" ? localStorage : null
): Record<string, unknown> {
    const base = config && typeof config === "object" ? { ...config } : {};
    return { ...base, ...loadDemoUiPrefs(storage) };
}

export function isDemoReadonlyRejection(errData: unknown): boolean {
    if (!errData || typeof errData !== "object") {
        return false;
    }
    return (errData as { code?: unknown }).code === "demo_readonly";
}
