// SPDX-License-Identifier: 0BSD

import { createRegistry } from "./registryCore.js";
import { registerRoute } from "./routeRegistry.js";
import { registerNavItem } from "./navRegistry.js";
import { registerTool } from "./toolsRegistry.js";
import { registerCommand } from "./commandRegistry.js";
import { registerSettingsSection } from "./settingsSectionRegistry.js";

/**
 * @typedef {Object} FeatureDefinition
 * @property {string} id
 * @property {import('./routeRegistry.js').FeatureRouteEntry[]} [routes]
 * @property {import('./coreNavEntries.js').NavEntry[]} [nav]
 * @property {import('./coreToolsEntries.js').ToolEntry[]} [tools]
 * @property {import('./coreCommandEntries.js').CommandEntry[]} [commands]
 * @property {{ id: string, keywords?: string[] }[]} [settingsSections]
 */

/** @type {import('./registryCore.js').Registry<{ id: string }>} */
const featureRegistry = createRegistry("featureRegistry");

/**
 * Register a feature module: routes plus optional contribution lists.
 * @param {FeatureDefinition} feature
 */
export function registerFeature(feature) {
    if (!feature?.id) {
        throw new Error("featureRegistry: feature requires an id");
    }
    featureRegistry.register({ id: feature.id });

    for (const route of feature.routes || []) {
        registerRoute(route);
    }
    for (const entry of feature.nav || []) {
        registerNavItem(entry);
    }
    for (const entry of feature.tools || []) {
        registerTool(entry);
    }
    for (const entry of feature.commands || []) {
        registerCommand(entry);
    }
    for (const section of feature.settingsSections || []) {
        registerSettingsSection(section);
    }
}

/**
 * @returns {string[]}
 */
export function listFeatureIds() {
    return featureRegistry.list().map((entry) => entry.id);
}

/**
 * Clear feature ids only (tests). Does not clear nested registries.
 */
export function clearFeatureIds() {
    featureRegistry.clear();
}
