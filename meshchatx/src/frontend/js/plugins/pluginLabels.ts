// SPDX-License-Identifier: 0BSD

import type { ApiClient } from "../apiClient.js";
import type { PluginManifest } from "./pluginManifest.js";

/**
 * Flatten nested locale objects into dotted keys for plugin worker translation.
 */
export function flattenLocaleMessages(messages: Record<string, unknown>, prefix = ""): Record<string, string> {
    const flat: Record<string, string> = {};
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
            Object.assign(flat, flattenLocaleMessages(value as Record<string, unknown>, path));
        }
    }
    return flat;
}

export async function loadPluginLabelMap(
    apiClient: ApiClient,
    pluginId: string,
    locale: string,
    manifest: Partial<PluginManifest> | Record<string, unknown> = {}
): Promise<Record<string, string>> {
    const i18n = (manifest as PluginManifest).i18n || {};
    const directory = i18n.directory || "locales";
    const defaultLocale = i18n.defaultLocale || "en";
    const candidates: string[] = [];
    for (const code of [locale, defaultLocale, "en"]) {
        if (code && !candidates.includes(code)) {
            candidates.push(code);
        }
    }
    for (const code of candidates) {
        try {
            const assetPath = `${directory}/${code}.json`;
            const version = (manifest as PluginManifest).version || "1";
            const response = await apiClient.get(
                `/api/v1/plugins/${encodeURIComponent(pluginId)}/asset/${assetPath}?v=${encodeURIComponent(version)}`,
                {
                    responseType: "json",
                }
            );
            if (response.data && typeof response.data === "object") {
                return flattenLocaleMessages(response.data as Record<string, unknown>);
            }
        } catch {
            // try next locale candidate
        }
    }
    return {};
}

export function resolvePluginUiString(
    labels: Record<string, string>,
    key: string,
    manifest: Partial<PluginManifest> | Record<string, unknown> = {}
): string {
    if (labels[key]) {
        return labels[key];
    }
    const record = manifest as Partial<PluginManifest>;
    if (key === "title") {
        return typeof record.name === "string" ? record.name : key;
    }
    if (key === "description") {
        return typeof record.description === "string" ? record.description : key;
    }
    if (key === "nav") {
        return typeof record.name === "string" ? record.name : key;
    }
    return key;
}
