// SPDX-License-Identifier: 0BSD

/** Reviewed host widgets plugins may request via manifest ui.widgets. */

export const HOST_WIDGET_NAMES = Object.freeze(["IssueStackView", "HashBadge"]);

/**
 * @param {string} name
 * @returns {boolean}
 */
export function isKnownHostWidget(name) {
    return HOST_WIDGET_NAMES.includes(name);
}

/**
 * Host widgets are rendered by PluginSlotNode.svelte.
 * Kept as a name allowlist only.
 * @param {string} name
 * @returns {string | null}
 */
export function resolveHostWidget(name) {
    return isKnownHostWidget(name) ? name : null;
}

/**
 * @param {string} name
 * @returns {Promise<string | null>}
 */
export function resolveHostWidgetAsync(name) {
    return Promise.resolve(resolveHostWidget(name));
}
