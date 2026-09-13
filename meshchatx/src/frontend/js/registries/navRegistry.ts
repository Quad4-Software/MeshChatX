// SPDX-License-Identifier: 0BSD

import { createRegistry } from "./registryCore.js";
import type { NavEntry } from "./coreNavEntries.js";

export type { NavEntry };

export const navRegistry = createRegistry<NavEntry>("navRegistry");

export function registerNavItem(entry: NavEntry) {
    navRegistry.register(entry);
}

export function unregisterNavItem(id: string) {
    navRegistry.unregister(id);
}

export function listNavItems(): NavEntry[] {
    return navRegistry.list();
}
