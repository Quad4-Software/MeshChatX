// SPDX-License-Identifier: 0BSD

import { createRegistry } from "./registryCore.js";

export type PageMountKind = "vue" | "svelte";

export interface FeatureRouteEntry {
    name: string;
    path: string;
    mount: PageMountKind;
    load: () => Promise<unknown>;
    props?: boolean;
    meta?: Record<string, unknown>;
    routeProps?: Record<string, unknown>;
}

export type RouteRegistryEntry = FeatureRouteEntry & { id: string };

export const routeRegistry = createRegistry<RouteRegistryEntry>("routeRegistry");

export function registerRoute(entry: FeatureRouteEntry) {
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

export function unregisterRoute(name: string) {
    routeRegistry.unregister(name);
}

export function listRoutes(): RouteRegistryEntry[] {
    return routeRegistry.list();
}

/**
 * Clear routes (tests).
 */
export function clearRoutes() {
    routeRegistry.clear();
}
