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

/**
 * @param {unknown} value
 * @param {number} max
 * @returns {string}
 */
export function clampUiString(value, max = MAX_UI_STRING_CHARS) {
    const text = value == null ? "" : String(value);
    if (text.length <= max) {
        return text;
    }
    return `${text.slice(0, max)}\n[truncated]`;
}

/**
 * @param {string} pluginId
 * @param {unknown} src
 * @returns {string | null}
 */
export function sanitizePluginAssetSrc(pluginId, src) {
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

/**
 * @typedef {{ ok: true, descriptor: object | null } | { ok: false, error: string }} UiValidateResult
 */

/**
 * @param {unknown} descriptor
 * @param {{ pluginId?: string, allowHtmlFrame?: boolean, allowedWidgets?: string[] }} [options]
 * @returns {UiValidateResult}
 */
export function validateUiDescriptor(descriptor, options: any = {}) {
    if (descriptor == null) {
        return { ok: true, descriptor: null };
    }
    if (typeof descriptor !== "object" || Array.isArray(descriptor)) {
        return { ok: false, error: "UI descriptor must be an object" };
    }

    let nodeCount = 0;
    const allowHtmlFrame = Boolean(options.allowHtmlFrame);
    const allowedWidgets = new Set(options.allowedWidgets || []);

    /**
     * @param {unknown} node
     * @param {number} depth
     * @returns {string | null}
     */
    function walk(node, depth) {
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

        const type = node.type;
        if (typeof type !== "string" || !KNOWN_NODE_TYPES.includes(type)) {
            return `Unknown UI node type: ${String(type)}`;
        }
        if (type === "html-frame" && !allowHtmlFrame) {
            return "html-frame requires ui:sandboxed-html permission";
        }
        if (type === "widget") {
            const name = typeof node.name === "string" ? node.name : "";
            if (!name || !allowedWidgets.has(name)) {
                return `Widget "${name || "?"}" is not allowed for this plugin`;
            }
        }
        if ((type === "image" || type === "html-frame") && options.pluginId) {
            const src = sanitizePluginAssetSrc(options.pluginId, node.src);
            if (node.src && !src) {
                return `${type} src must be a plugin asset URL`;
            }
            if (type === "html-frame") {
                node.src = src || "";
            }
        }

        for (const key of ["value", "label", "title", "description", "placeholder", "emptyText", "srcdoc"]) {
            if (typeof node[key] === "string" && node[key].length > MAX_UI_STRING_CHARS) {
                node[key] = clampUiString(node[key]);
            }
        }

        const childLists = [];
        if (Array.isArray(node.children)) {
            childLists.push(node.children);
        }
        if (Array.isArray(node.items)) {
            childLists.push(node.items);
        }
        if (Array.isArray(node.tabs)) {
            childLists.push(node.tabs);
        }
        if (Array.isArray(node.panels)) {
            childLists.push(node.panels);
        }
        if (Array.isArray(node.rows)) {
            for (const row of node.rows) {
                if (Array.isArray(row)) {
                    childLists.push(row);
                } else if (row && typeof row === "object" && Array.isArray(row.cells)) {
                    childLists.push(row.cells);
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
    return { ok: true, descriptor: /** @type {object} */ (descriptor) };
}
