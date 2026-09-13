// SPDX-License-Identifier: 0BSD

const labelsByPlugin = new Map<string, Record<string, string>>();

export function setPluginUiLabels(pluginId: string, labels: Record<string, string>): void {
    labelsByPlugin.set(pluginId, labels);
}

export function clearPluginUiLabels(pluginId: string): void {
    labelsByPlugin.delete(pluginId);
}

export function getPluginUiLabels(pluginId: string): Record<string, string> {
    return labelsByPlugin.get(pluginId) || {};
}
