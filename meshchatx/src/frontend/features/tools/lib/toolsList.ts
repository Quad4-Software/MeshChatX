// SPDX-License-Identifier: 0BSD

import { listRoutes } from "../../../js/registries/routeRegistry.js";
import { listTools } from "../../../js/registries/toolsRegistry.js";

export const TOOL_GROUP_ORDER = ["diagnostics", "transfer", "messaging", "network", "other"] as const;

/** Route names whose hashRouter path is under /tools/ */
const TOOLS_PREFIXED_ROUTE_NAMES = new Set([
    "paper-message",
    "sieve-filters",
    "message-blocklist",
    "rnode-flasher",
    "repository-server",
    "reticulum-config-editor",
]);

export type ToolRouteRef = { name?: string; path?: string } | string | null | undefined;

export type ToolRecord = Record<string, unknown> & {
    title?: string;
    titleKey?: string;
    description?: string;
    descriptionKey?: string;
    name?: string;
    group?: string;
    customClass?: string;
    comingSoon?: boolean;
    route?: ToolRouteRef;
};

export type ToolGroup = {
    id: string;
    tools: ToolRecord[];
};

/**
 * Build a hash href from a tool.route value ({ name }, { path }, or string).
 */
export function toolRouteHref(route: ToolRouteRef): string {
    if (!route) {
        return "";
    }
    if (typeof route === "string") {
        const path = route.startsWith("/") ? route : `/${route}`;
        return `#${path}`;
    }
    if (route.path) {
        const path = route.path.startsWith("/") ? route.path : `/${route.path}`;
        return `#${path}`;
    }
    const name = route.name;
    if (!name) {
        return "";
    }
    try {
        const registered = listRoutes().find((entry) => entry.name === name);
        if (registered?.path) {
            const path = registered.path.startsWith("/") ? registered.path : `/${registered.path}`;
            return `#${path}`;
        }
    } catch {
        // routeRegistry may be empty in isolated tests
    }
    if (TOOLS_PREFIXED_ROUTE_NAMES.has(name)) {
        return `#/tools/${name}`;
    }
    return `#/${name}`;
}

export function translateTools(t: (key: string, params?: Record<string, unknown>) => string): ToolRecord[] {
    return listTools().map((tool: ToolRecord) => ({
        ...tool,
        title: tool.title || (tool.titleKey ? t(tool.titleKey) : ""),
        description: tool.description || (tool.descriptionKey ? t(tool.descriptionKey) : ""),
    }));
}

export function filterTools(tools: ToolRecord[], searchQuery: string): ToolRecord[] {
    if (!searchQuery.trim()) {
        return tools;
    }
    const query = searchQuery.toLowerCase().trim();
    return tools.filter((tool) => {
        const title = String(tool.title || "").toLowerCase();
        const description = String(tool.description || "").toLowerCase();
        const name = String(tool.name || "").toLowerCase();
        return title.includes(query) || description.includes(query) || name.includes(query);
    });
}

export function groupTools(tools: ToolRecord[]): ToolGroup[] {
    const groups: Record<string, ToolRecord[]> = {};
    for (const tool of tools) {
        const groupId = String(tool.group || "other");
        if (!groups[groupId]) {
            groups[groupId] = [];
        }
        groups[groupId].push(tool);
    }
    return TOOL_GROUP_ORDER.filter((groupId) => groups[groupId]?.length).map((groupId) => ({
        id: groupId,
        tools: groups[groupId],
    }));
}

export function toolRowClass(tool: ToolRecord): string {
    return ["tool-row", tool.customClass, tool.comingSoon ? "opacity-60 grayscale-[0.5] cursor-default" : ""]
        .filter(Boolean)
        .join(" ");
}

const COLLAPSED_STORAGE_KEY = "meshchatx.tools.collapsedSections";

export function loadCollapsedSections(): Record<string, boolean> {
    try {
        const raw = localStorage.getItem(COLLAPSED_STORAGE_KEY);
        if (!raw) {
            return {};
        }
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
            return parsed as Record<string, boolean>;
        }
    } catch {
        // ignore corrupt storage
    }
    return {};
}

export function saveCollapsedSections(map: Record<string, boolean>): void {
    try {
        localStorage.setItem(COLLAPSED_STORAGE_KEY, JSON.stringify(map));
    } catch {
        // ignore quota / private mode
    }
}
