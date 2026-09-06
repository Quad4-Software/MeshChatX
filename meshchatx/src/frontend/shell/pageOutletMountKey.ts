// SPDX-License-Identifier: 0BSD

/**
 * Remount identity for PageOutlet hosts.
 * Matches Vue App.vue RouterView keying:
 * - stableKey: route.name (props update, no remount on conversation switch)
 * - keepAlive: route.name (cache entry survives param changes)
 * - default: name + fullPath (query/hash changes remount)
 */

export interface MountKeyRoute {
    name: string;
    fullPath: string;
    meta?: Record<string, unknown> | null;
}

export function pageOutletMountKey(route: MountKeyRoute): string {
    if (route.meta?.stableKey || route.meta?.keepAlive) {
        return String(route.name);
    }
    return `${route.name}:${route.fullPath}`;
}
