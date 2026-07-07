// SPDX-License-Identifier: 0BSD

import { createRegistry } from "./registryCore.js";

/** @typedef {import('./coreCommandEntries.js').CommandEntry} CommandEntry */

/** @type {import('./registryCore.js').Registry<CommandEntry>} */
export const commandRegistry = createRegistry("commandRegistry");

/**
 * @param {CommandEntry} entry
 */
export function registerCommand(entry) {
    commandRegistry.register(entry);
}

/**
 * @param {string} id
 */
export function unregisterCommand(id) {
    commandRegistry.unregister(id);
}

/**
 * @returns {CommandEntry[]}
 */
export function listCommands() {
    return commandRegistry.list();
}
