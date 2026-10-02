// SPDX-License-Identifier: 0BSD

import { createRegistry } from "./registryCore";
import type { NavEntry } from "./coreNavEntries";

export const navRegistry = createRegistry<NavEntry>("navRegistry");

export function registerNavItem(entry: NavEntry): void {
    navRegistry.register(entry);
}

export function unregisterNavItem(id: string): void {
    navRegistry.unregister(id);
}

export function listNavItems(): NavEntry[] {
    return navRegistry.list();
}
