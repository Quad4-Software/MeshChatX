// SPDX-License-Identifier: 0BSD AND MIT

import { listRoutes } from "../../../js/registries/routeRegistry.js";
import { listTools } from "../../../js/registries/toolsRegistry.js";

export const TOOL_GROUP_ORDER = ["diagnostics", "transfer", "messaging", "network", "other"];

/** Route names whose vue-router path is under /tools/ */
const TOOLS_PREFIXED_ROUTE_NAMES = new Set([
    "paper-message",
    "sieve-filters",
    "message-blocklist",
    "rnode-flasher",
    "repository-server",
    "reticulum-config-editor",
]);

/**
 * Build a hash href from a tool.route value ({ name }, { path }, or string).
 * @param {{ name?: string, path?: string } | string | null | undefined} route
 * @returns {string}
 */
export function toolRouteHref(route) {
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

/**
 * @param {(key: string, params?: Record<string, unknown>) => string} t
 * @returns {Array<Record<string, unknown>>}
 */
export function translateTools(t) {
    return listTools().map((tool) => ({
        ...tool,
        title: tool.title || (tool.titleKey ? t(tool.titleKey) : ""),
        description: tool.description || (tool.descriptionKey ? t(tool.descriptionKey) : ""),
    }));
}

/**
 * @param {Array<Record<string, unknown>>} tools
 * @param {string} searchQuery
 * @returns {Array<Record<string, unknown>>}
 */
export function filterTools(tools, searchQuery) {
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

/**
 * @param {Array<Record<string, unknown>>} tools
 * @returns {Array<{ id: string, tools: Array<Record<string, unknown>> }> | null}
 */
export function groupTools(tools) {
    /** @type {Record<string, Array<Record<string, unknown>>>} */
    const groups = {};
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

/**
 * @param {Record<string, unknown>} tool
 * @returns {string}
 */
export function toolRowClass(tool) {
    return ["tool-row", tool.customClass, tool.comingSoon ? "opacity-60 grayscale-[0.5] cursor-default" : ""]
        .filter(Boolean)
        .join(" ");
}

const COLLAPSED_STORAGE_KEY = "meshchatx.tools.collapsedSections";

/**
 * @returns {Record<string, boolean>}
 */
export function loadCollapsedSections() {
    try {
        const raw = localStorage.getItem(COLLAPSED_STORAGE_KEY);
        if (!raw) {
            return {};
        }
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
            return /** @type {Record<string, boolean>} */ (parsed);
        }
    } catch {
        // ignore corrupt storage
    }
    return {};
}

/**
 * @param {Record<string, boolean>} map
 */
export function saveCollapsedSections(map) {
    try {
        localStorage.setItem(COLLAPSED_STORAGE_KEY, JSON.stringify(map));
    } catch {
        // ignore quota / private mode
    }
}
