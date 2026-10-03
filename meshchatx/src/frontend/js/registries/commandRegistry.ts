// SPDX-License-Identifier: 0BSD

import { createRegistry } from "./registryCore";

export type CommandType = "navigation" | "action";

export interface CommandEntry {
    id: string;
    title: string;
    description: string;
    icon: string;
    type: CommandType;
    route?: { name: string };
    action?: string;
    pluginId?: string | null;
}

export const commandRegistry = createRegistry<CommandEntry>("commandRegistry");

export function registerCommand(entry: CommandEntry): void {
    commandRegistry.register(entry);
}

export function unregisterCommand(id: string): void {
    commandRegistry.unregister(id);
}

export function listCommands(): CommandEntry[] {
    return commandRegistry.list();
}
