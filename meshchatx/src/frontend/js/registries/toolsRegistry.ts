// SPDX-License-Identifier: 0BSD

import { createRegistry } from "./registryCore.js";

/** @typedef {import('./coreToolsEntries.js').ToolEntry} ToolEntry */

/** @type {import('./registryCore.js').Registry<ToolEntry>} */
export const toolsRegistry = createRegistry("toolsRegistry");

/**
 * @param {ToolEntry} entry
 */
export function registerTool(entry) {
    toolsRegistry.register({ ...entry, id: entry.name });
}

/**
 * @param {string} name
 */
export function unregisterTool(name) {
    toolsRegistry.unregister(name);
}

/**
 * @returns {ToolEntry[]}
 */
export function listTools() {
    return toolsRegistry.list().map((entry) => {
        const tool: any = { ...entry };
        delete tool.id;
        return tool;
    });
}
