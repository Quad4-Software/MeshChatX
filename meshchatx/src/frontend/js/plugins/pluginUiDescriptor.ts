// SPDX-License-Identifier: 0BSD

/** Versioned plugin UI descriptor schema (uiDescriptor v1). */

export const UI_DESCRIPTOR_VERSION = 1;

export const KNOWN_NODE_TYPES = Object.freeze([
    "text",
    "input",
    "checkbox",
    "button",
    "badge",
    "actions",
    "section",
    "list",
    "row",
    "column",
    "tabs",
    "select",
    "number",
    "progress",
    "separator",
    "table",
    "code",
    "empty",
    "image",
    "widget",
    "html-frame",
]);

export const MAX_UI_DEPTH = 24;
export const MAX_UI_NODES = 800;
export const MAX_UI_STRING_CHARS = 120_000;

export type UiValidateOptions = {
    pluginId?: string;
    allowHtmlFrame?: boolean;
    allowedWidgets?: string[];
};

export type UiValidateResult = { ok: true; descriptor: Record<string, unknown> | null } | { ok: false; error: string };

export function clampUiString(value: unknown, max: number = MAX_UI_STRING_CHARS): string {
    const text = value == null ? "" : String(value);
    if (text.length <= max) {
        return text;
    }
    return `${text.slice(0, max)}\n[truncated]`;
}

export function sanitizePluginAssetSrc(pluginId: string, src: unknown): string | null {
    if (typeof src !== "string" || !src.trim()) {
        return null;
    }
    const prefix = `/api/v1/plugins/${encodeURIComponent(pluginId)}/asset/`;
    if (!src.startsWith(prefix) && !src.startsWith(`/api/v1/plugins/${pluginId}/asset/`)) {
        return null;
    }
    if (src.includes("..") || src.includes("://")) {
        return null;
    }
    return src;
}

export function validateUiDescriptor(descriptor: unknown, options: UiValidateOptions = {}): UiValidateResult {
    if (descriptor == null) {
        return { ok: true, descriptor: null };
    }
    if (typeof descriptor !== "object" || Array.isArray(descriptor)) {
        return { ok: false, error: "UI descriptor must be an object" };
    }

    let nodeCount = 0;
    const allowHtmlFrame = Boolean(options.allowHtmlFrame);
    const allowedWidgets = new Set(options.allowedWidgets || []);

    function walk(node: unknown, depth: number): string | null {
        if (node == null) {
            return null;
        }
        if (typeof node !== "object" || Array.isArray(node)) {
            return "UI nodes must be objects";
        }
        if (depth > MAX_UI_DEPTH) {
            return `UI descriptor exceeds max depth ${MAX_UI_DEPTH}`;
        }
        nodeCount += 1;
        if (nodeCount > MAX_UI_NODES) {
            return `UI descriptor exceeds max nodes ${MAX_UI_NODES}`;
        }

        const record = node as Record<string, any>;
        const type = record.type;
        if (typeof type !== "string" || !(KNOWN_NODE_TYPES as readonly string[]).includes(type)) {
            return `Unknown UI node type: ${String(type)}`;
        }
        if (type === "html-frame" && !allowHtmlFrame) {
            return "html-frame requires ui:sandboxed-html permission";
        }
        if (type === "widget") {
            const name = typeof record.name === "string" ? record.name : "";
            if (!name || !allowedWidgets.has(name)) {
                return `Widget "${name || "?"}" is not allowed for this plugin`;
            }
        }
        if ((type === "image" || type === "html-frame") && options.pluginId) {
            const src = sanitizePluginAssetSrc(options.pluginId, record.src);
            if (record.src && !src) {
                return `${type} src must be a plugin asset URL`;
            }
            if (type === "html-frame") {
                record.src = src || "";
            }
        }

        for (const key of ["value", "label", "title", "description", "placeholder", "emptyText", "srcdoc"]) {
            if (typeof record[key] === "string" && record[key].length > MAX_UI_STRING_CHARS) {
                record[key] = clampUiString(record[key]);
            }
        }

        const childLists: unknown[][] = [];
        if (Array.isArray(record.children)) {
            childLists.push(record.children);
        }
        if (Array.isArray(record.items)) {
            childLists.push(record.items);
        }
        if (Array.isArray(record.tabs)) {
            childLists.push(record.tabs);
        }
        if (Array.isArray(record.panels)) {
            childLists.push(record.panels);
        }
        if (Array.isArray(record.rows)) {
            for (const row of record.rows) {
                if (Array.isArray(row)) {
                    childLists.push(row);
                } else if (row && typeof row === "object" && Array.isArray((row as { cells?: unknown }).cells)) {
                    childLists.push((row as { cells: unknown[] }).cells);
                }
            }
        }

        for (const list of childLists) {
            for (const child of list) {
                const err = walk(child, depth + 1);
                if (err) {
                    return err;
                }
            }
        }
        return null;
    }

    const error = walk(descriptor, 0);
    if (error) {
        return { ok: false, error };
    }
    return { ok: true, descriptor: descriptor as Record<string, unknown> };
}
