// SPDX-License-Identifier: 0BSD

import { createRegistry } from "./registryCore.js";

/** @typedef {import('./coreNavEntries.js').NavEntry} NavEntry */

/** @type {import('./registryCore.js').Registry<NavEntry>} */
export const navRegistry = createRegistry("navRegistry");

/**
 * @param {NavEntry} entry
 */
export function registerNavItem(entry) {
    navRegistry.register(entry);
}

/**
 * @param {string} id
 */
export function unregisterNavItem(id) {
    navRegistry.unregister(id);
}

/**
 * @returns {NavEntry[]}
 */
export function listNavItems() {
    return navRegistry.list();
}
