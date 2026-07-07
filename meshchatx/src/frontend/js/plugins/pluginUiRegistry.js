// SPDX-License-Identifier: 0BSD

/** @type {Map<string, Record<string, string>>} */
const labelsByPlugin = new Map();

/**
 * @param {string} pluginId
 * @param {Record<string, string>} labels
 */
export function setPluginUiLabels(pluginId, labels) {
    labelsByPlugin.set(pluginId, labels);
}

/**
 * @param {string} pluginId
 */
export function clearPluginUiLabels(pluginId) {
    labelsByPlugin.delete(pluginId);
}

/**
 * @param {string} pluginId
 * @returns {Record<string, string>}
 */
export function getPluginUiLabels(pluginId) {
    return labelsByPlugin.get(pluginId) || {};
}
