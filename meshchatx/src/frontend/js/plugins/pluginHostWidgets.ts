// SPDX-License-Identifier: 0BSD

/** Reviewed host widgets plugins may request via manifest ui.widgets. */

export const HOST_WIDGET_NAMES = Object.freeze(["IssueStackView", "HashBadge"]);

export function isKnownHostWidget(name: string): boolean {
    return (HOST_WIDGET_NAMES as readonly string[]).includes(name);
}

/**
 * Host widgets are rendered by PluginSlotNode.svelte.
 * Kept as a name allowlist only.
 */
export function resolveHostWidget(name: string): string | null {
    return isKnownHostWidget(name) ? name : null;
}

export function resolveHostWidgetAsync(name: string): Promise<string | null> {
    return Promise.resolve(resolveHostWidget(name));
}
