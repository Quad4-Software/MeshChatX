// SPDX-License-Identifier: 0BSD

import { declaredPermissionIds, manifestPermissionSummary as summarizePermissions } from "./pluginPermissions.js";

const SUPPORTED_API_VERSION = 1;

/**
 * @typedef {Object} PluginManifest
 * @property {string} id
 * @property {string} version
 * @property {string | number} apiVersion
 * @property {string} [name]
 * @property {string} [description]
 * @property {{ entry: string, type: 'js' | 'wasm' }} [frontend]
 * @property {{ entry: string, type: 'wasm' | 'python' }} [backend]
 * @property {Object} [contributes]
 * @property {Object} [permissions]
 * @property {{ endpoints?: string[] }} [network]
 */

/**
 * @param {unknown} manifest
 * @returns {PluginManifest}
 */
export function validatePluginManifest(manifest) {
    if (!manifest || typeof manifest !== "object") {
        throw new Error("Plugin manifest must be an object");
    }
    const record = /** @type {Record<string, unknown>} */ (manifest);
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
        const frontend = /** @type {Record<string, unknown>} */ (record.frontend);
        if (typeof frontend.entry !== "string" || !frontend.entry.trim()) {
            throw new Error("Plugin frontend.entry is required when frontend is set");
        }
        if (frontend.type !== "js" && frontend.type !== "wasm") {
            throw new Error("Plugin frontend.type must be js or wasm");
        }
    }
    if (record.backend != null) {
        const backend = /** @type {Record<string, unknown>} */ (record.backend);
        if (typeof backend.entry !== "string" || !backend.entry.trim()) {
            throw new Error("Plugin backend.entry is required when backend is set");
        }
        if (backend.type !== "wasm" && backend.type !== "python") {
            throw new Error("Plugin backend.type must be wasm or python");
        }
    }
    const permissions = record.permissions ?? {};
    if (permissions && typeof permissions !== "object") {
        throw new Error("Plugin permissions must be an object");
    }
    if (record.network != null && typeof record.network !== "object") {
        throw new Error("Plugin network must be an object");
    }
    return /** @type {PluginManifest} */ (manifest);
}

/**
 * @param {PluginManifest} manifest
 * @param {(key: string, values?: Record<string, unknown>) => string} [t]
 * @returns {string[]}
 */
export function manifestPermissionSummary(manifest, t) {
    const translate = t || ((key) => key);
    return summarizePermissions(manifest, translate);
}

export { SUPPORTED_API_VERSION, declaredPermissionIds };
