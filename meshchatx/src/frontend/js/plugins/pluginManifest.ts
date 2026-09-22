// SPDX-License-Identifier: 0BSD

import { declaredPermissionIds, manifestPermissionSummary as summarizePermissions } from "./pluginPermissions.js";

const SUPPORTED_API_VERSION = 1;

export type PluginFrontend = {
    entry: string;
    type: "js" | "wasm";
};

export type PluginBackend = {
    entry: string;
    type: "wasm" | "python";
};

export type PluginUiConfig = {
    widgets?: string[];
};

export type PluginI18nConfig = {
    directory?: string;
    defaultLocale?: string;
};

export type PluginPermissions = {
    hooks?: string[];
    managers?: string[];
    storage?: string;
    network?: unknown;
    ui?: "sandboxed-html" | "none" | Array<"sandboxed-html" | "none">;
    [key: string]: unknown;
};

export type PluginContributes = {
    navItems?: Array<Record<string, unknown>>;
    toolsPageEntries?: Array<Record<string, unknown>>;
    [key: string]: unknown;
};

export type PluginManifest = {
    id: string;
    version: string;
    apiVersion: string | number;
    name?: string;
    description?: string;
    frontend?: PluginFrontend;
    backend?: PluginBackend;
    ui?: PluginUiConfig;
    i18n?: PluginI18nConfig;
    contributes?: PluginContributes;
    permissions?: PluginPermissions;
    network?: { endpoints?: string[] };
    declared_permissions?: string[];
};

export type ManifestTranslateFn = (key: string, values?: Record<string, unknown>) => string;

export function validatePluginManifest(manifest: unknown): PluginManifest {
    if (!manifest || typeof manifest !== "object") {
        throw new Error("Plugin manifest must be an object");
    }
    const record = manifest as Record<string, unknown>;
    if (typeof record.id !== "string" || !record.id.trim()) {
        throw new Error("Plugin manifest requires a non-empty id");
    }
    if (typeof record.version !== "string" || !record.version.trim()) {
        throw new Error("Plugin manifest requires a version");
    }
    const apiVersion = Number(record.apiVersion);
    if (!Number.isFinite(apiVersion) || apiVersion !== SUPPORTED_API_VERSION) {
        throw new Error(`Plugin apiVersion must be ${SUPPORTED_API_VERSION}`);
    }
    if (record.frontend != null) {
        const frontend = record.frontend as Record<string, unknown>;
        if (typeof frontend.entry !== "string" || !frontend.entry.trim()) {
            throw new Error("Plugin frontend.entry is required when frontend is set");
        }
        if (frontend.type === "wasm") {
            throw new Error("Plugin frontend.type wasm is not implemented yet");
        }
        if (frontend.type !== "js") {
            throw new Error("Plugin frontend.type must be js");
        }
    }
    if (record.backend != null) {
        const backend = record.backend as Record<string, unknown>;
        if (typeof backend.entry !== "string" || !backend.entry.trim()) {
            throw new Error("Plugin backend.entry is required when backend is set");
        }
        if (backend.type !== "wasm" && backend.type !== "python") {
            throw new Error("Plugin backend.type must be wasm or python");
        }
    }
    if (record.ui != null) {
        const ui = record.ui as Record<string, unknown>;
        if (ui.widgets != null) {
            if (!Array.isArray(ui.widgets)) {
                throw new Error("Plugin ui.widgets must be an array");
            }
            for (const widget of ui.widgets) {
                if (typeof widget !== "string" || !widget.trim()) {
                    throw new Error("Plugin ui.widgets entries must be non-empty strings");
                }
            }
        }
    }
    const permissions = record.permissions ?? {};
    if (permissions && typeof permissions !== "object") {
        throw new Error("Plugin permissions must be an object");
    }
    if (permissions && typeof permissions === "object") {
        const uiPerm = (permissions as Record<string, unknown>).ui;
        if (uiPerm != null && uiPerm !== "sandboxed-html" && uiPerm !== "none") {
            if (!Array.isArray(uiPerm) || uiPerm.some((v) => v !== "sandboxed-html")) {
                throw new Error("Plugin permissions.ui must be none, sandboxed-html, or an array of those values");
            }
        }
    }
    if (record.network != null && typeof record.network !== "object") {
        throw new Error("Plugin network must be an object");
    }
    return manifest as PluginManifest;
}

export function manifestPermissionSummary(manifest: PluginManifest, t?: ManifestTranslateFn): string[] {
    const translate = t || ((key: string) => key);
    return summarizePermissions(manifest, translate);
}

export { SUPPORTED_API_VERSION, declaredPermissionIds };
