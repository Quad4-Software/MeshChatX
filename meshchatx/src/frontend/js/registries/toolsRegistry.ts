// SPDX-License-Identifier: 0BSD

import { createRegistry } from "./registryCore";

export interface ToolEntry {
    name: string;
    route?: { name: string } | null;
    icon?: string | null;
    iconBg?: string;
    titleKey?: string;
    descriptionKey?: string;
    title?: string;
    description?: string;
    alpha?: boolean;
    beta?: boolean;
    comingSoon?: boolean;
    customClass?: string;
    image?: string;
    imageClass?: string;
    imageAlt?: string;
    extraAction?: { href: string; target: string; icon: string };
    pluginId?: string | null;
    group?: "diagnostics" | "transfer" | "messaging" | "network" | "other";
    id?: string;
}

export const toolsRegistry = createRegistry<ToolEntry & { id: string }>("toolsRegistry");

export function registerTool(entry: ToolEntry): void {
    toolsRegistry.register({ ...entry, id: entry.name });
}

export function unregisterTool(name: string): void {
    toolsRegistry.unregister(name);
}

export function listTools(): ToolEntry[] {
    return toolsRegistry.list().map((entry) => {
        const tool = { ...entry };
        delete tool.id;
        return tool;
    });
}
