// SPDX-License-Identifier: 0BSD

/**
 * Pure helpers and HTTP-backed config load/patch for settings UI.
 */

import type { ApiClient } from "../apiClient.js";
import { mergeGlobalConfig } from "../GlobalState.js";
import GlobalEmitter from "../GlobalEmitter.js";
import { sanitizeThemeConfigFields } from "../../theme/themeEngine.js";

export function numOrNull(v: unknown): number | null {
    if (v === null || v === undefined || v === "") {
        return null;
    }
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
}

/** Normalizes hex color fields on a config object in place. */
export function sanitizeColorConfigFields(config: Record<string, unknown> | null | undefined): void {
    if (!config) return;
    sanitizeThemeConfigFields(config as Parameters<typeof sanitizeThemeConfigFields>[0]);
    const hex6 = (value: unknown, fallback: string): string => {
        if (value == null || value === "") {
            return fallback;
        }
        if (typeof value === "string" && /^#[0-9A-Fa-f]{6}$/.test(value.trim())) {
            return value.trim();
        }
        return fallback;
    };
    config.banished_color = hex6(config.banished_color, "#dc2626");
    config.message_outbound_bubble_color = hex6(config.message_outbound_bubble_color, "#4f46e5");
    config.message_failed_bubble_color = hex6(config.message_failed_bubble_color, "#ef4444");
    config.message_waiting_bubble_color = hex6(config.message_waiting_bubble_color, "#e5e7eb");
    const inbound = config.message_inbound_bubble_color;
    if (inbound == null || inbound === "") {
        config.message_inbound_bubble_color = null;
    } else if (typeof inbound === "string" && /^#[0-9A-Fa-f]{6}$/.test(inbound.trim())) {
        config.message_inbound_bubble_color = inbound.trim();
    } else {
        config.message_inbound_bubble_color = null;
    }
}

export async function fetchMergedConfig(
    api: Pick<ApiClient, "get">,
    baseConfig: Record<string, unknown>
): Promise<Record<string, unknown> | null> {
    const response = await api.get<{ config?: Record<string, unknown> }>("/api/v1/config");
    if (response?.data?.config) {
        return { ...baseConfig, ...response.data.config };
    }
    return null;
}

export async function patchServerConfig(
    partial: Record<string, unknown>,
    api: Pick<ApiClient, "patch">
): Promise<Record<string, unknown>> {
    const response = await api.patch<{ config: Record<string, unknown> }>("/api/v1/config", partial);
    return response.data.config;
}

/** Merge a server config snapshot into global state and notify the app shell. */
export function publishPatchedConfig(newConfig: Record<string, unknown> | null | undefined): void {
    if (!newConfig || typeof newConfig !== "object") {
        return;
    }
    mergeGlobalConfig(newConfig);
    GlobalEmitter.emit("config-updated", newConfig);
}
