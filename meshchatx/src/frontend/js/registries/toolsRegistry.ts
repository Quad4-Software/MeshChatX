// SPDX-License-Identifier: 0BSD

import { createRegistry } from "./registryCore.js";
import type { ToolEntry } from "./coreToolsEntries.js";

export type { ToolEntry };

export const toolsRegistry = createRegistry<ToolEntry & { id: string }>("toolsRegistry");

export function registerTool(entry: ToolEntry) {
    toolsRegistry.register({ ...entry, id: entry.name });
}

export function unregisterTool(name: string) {
    toolsRegistry.unregister(name);
}

export function listTools(): ToolEntry[] {
    return toolsRegistry.list().map((entry) => {
        const tool: any = { ...entry };
        delete tool.id;
        return tool;
    });
}
