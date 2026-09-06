// SPDX-License-Identifier: 0BSD

/**
 * Locale pack loading for svelte-i18n.
 */

import { addMessages, getLocaleFromNavigator, init, locale, _ as translateStore } from "svelte-i18n";
import { get } from "svelte/store";
import { registerFallbackMessages, registerTranslator } from "./i18n.js";

const localeModules = import.meta.glob("../locales/*.json");

const loadedLocales = new Set<string>();

const UI_LOCALE_ALIASES: Record<string, string> = {
    "zh-cn": "zh",
    zh_cn: "zh",
};

export function listLocaleCodes(): string[] {
    return Object.keys(localeModules)
        .map((filePath) => {
            const match = filePath.match(/\/([^/]+)\.json$/);
            return match ? match[1] : null;
        })
        .filter((code): code is string => Boolean(code))
        .sort((a, b) => {
            if (a === "en") return -1;
            if (b === "en") return 1;
            return a.localeCompare(b);
        });
}

export function normalizeUiLocaleCode(code: string | null | undefined | unknown): string {
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

async function loadLocaleMessages(code: string): Promise<Record<string, unknown> | null> {
    const loader = localeModules[`../locales/${code}.json`];
    if (!loader) {
        return null;
    }
    const mod = (await loader()) as { default?: Record<string, unknown> };
    return (mod.default || mod) as Record<string, unknown>;
}

export async function ensureLocaleMessages(_unused: unknown, code: string): Promise<boolean> {
    if (!code || typeof code !== "string") {
        return false;
    }
    if (loadedLocales.has(code)) {
        return true;
    }
    const messages = await loadLocaleMessages(code);
    if (!messages) {
        return false;
    }
    addMessages(code, messages as any);
    loadedLocales.add(code);
    return true;
}

export async function setLocale(_unused: unknown, code: string): Promise<boolean> {
    const normalized = normalizeUiLocaleCode(code);
    const ok = await ensureLocaleMessages(null, normalized);
    if (!ok) {
        return false;
    }
    locale.set(normalized);
    if (typeof document !== "undefined") {
        document.documentElement.lang = normalized;
    }
    if (typeof localStorage !== "undefined") {
        localStorage.setItem("meshchatx_ui_locale", normalized);
    }
    return true;
}

export function getCurrentUiLocale(): string {
    try {
        const code = get(locale);
        return normalizeUiLocaleCode(typeof code === "string" ? code : "en");
    } catch {
        return "en";
    }
}

/** @deprecated No-op kept for older call sites and tests. */
export function registerUiI18n(_unused?: unknown): void {
    // svelte-i18n is initialized via initSvelteI18n
}

export async function initSvelteI18n(enMessages: Record<string, unknown>): Promise<void> {
    addMessages("en", enMessages as any);
    loadedLocales.add("en");
    registerFallbackMessages(enMessages);
    registerTranslator((key, values) => {
        const fn = get(translateStore);
        if (typeof fn !== "function") {
            return key;
        }
        try {
            return String(
                fn(key, values ? { values: values as Record<string, string | number | boolean | Date> } : undefined)
            );
        } catch {
            return key;
        }
    });

    const initial =
        normalizeUiLocaleCode(
            (typeof localStorage !== "undefined" &&
                (localStorage.getItem("meshchatx_ui_locale") || localStorage.getItem("meshchatx_locale"))) ||
                getLocaleFromNavigator() ||
                "en"
        ) || "en";

    if (initial !== "en") {
        await ensureLocaleMessages(null, initial);
    }

    init({
        fallbackLocale: "en",
        initialLocale: initial,
    });

    if (typeof document !== "undefined") {
        document.documentElement.lang = initial;
    }
}
