// SPDX-License-Identifier: 0BSD

import { createRegistry } from "./registryCore.js";
import type { CommandEntry } from "./coreCommandEntries.js";

export type { CommandEntry };

export const commandRegistry = createRegistry<CommandEntry>("commandRegistry");

export function registerCommand(entry: CommandEntry) {
    commandRegistry.register(entry);
}

export function unregisterCommand(id: string) {
    commandRegistry.unregister(id);
}

export function listCommands(): CommandEntry[] {
    return commandRegistry.list();
}
