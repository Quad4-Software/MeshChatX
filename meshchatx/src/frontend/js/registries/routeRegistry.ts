// SPDX-License-Identifier: 0BSD

import { createRegistry } from "./registryCore.js";

/**
 * @typedef {"vue" | "svelte"} PageMountKind
 */

/**
 * @typedef {Object} FeatureRouteEntry
 * @property {string} name
 * @property {string} path
 * @property {PageMountKind} mount
 * @property {() => Promise<unknown>} load
 * @property {boolean} [props]
 * @property {Record<string, unknown>} [meta]
 * @property {Record<string, unknown>} [routeProps]
 */

/** @type {import('./registryCore.js').Registry<FeatureRouteEntry & { id: string }>} */
export const routeRegistry = createRegistry("routeRegistry");

/**
 * @param {FeatureRouteEntry} entry
 */
export function registerRoute(entry) {
    if (!entry?.name || !entry?.path) {
        throw new Error("routeRegistry: entry requires name and path");
    }
    if (entry.mount !== "vue" && entry.mount !== "svelte") {
        throw new Error(`routeRegistry: invalid mount "${entry.mount}"`);
    }
    if (typeof entry.load !== "function") {
        throw new Error("routeRegistry: entry requires load()");
    }
    routeRegistry.register({
        ...entry,
        id: entry.name,
        meta: entry.meta && typeof entry.meta === "object" ? entry.meta : {},
    });
}

/**
 * @param {string} name
 */
export function unregisterRoute(name) {
    routeRegistry.unregister(name);
}

/**
 * @returns {Array<FeatureRouteEntry & { id: string }>}
 */
export function listRoutes() {
    return routeRegistry.list();
}

/**
 * Clear routes (tests).
 */
export function clearRoutes() {
    routeRegistry.clear();
}
