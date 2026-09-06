// SPDX-License-Identifier: 0BSD

import { createRegistry } from "./registryCore.js";
import { registerRoute, type FeatureRouteEntry } from "./routeRegistry.js";
import { registerNavItem } from "./navRegistry.js";
import { registerTool } from "./toolsRegistry.js";
import { registerCommand } from "./commandRegistry.js";
import { registerSettingsSection, type SettingsSectionEntry } from "./settingsSectionRegistry.js";
import type { NavEntry } from "./coreNavEntries.js";
import type { ToolEntry } from "./coreToolsEntries.js";
import type { CommandEntry } from "./coreCommandEntries.js";

export interface FeatureDefinition {
    id: string;
    routes?: FeatureRouteEntry[];
    nav?: NavEntry[];
    tools?: ToolEntry[];
    commands?: CommandEntry[];
    settingsSections?: SettingsSectionEntry[];
}

const featureRegistry = createRegistry<{ id: string }>("featureRegistry");

/** Register a feature module: routes plus optional contribution lists. */
export function registerFeature(feature: FeatureDefinition): void {
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

export function listFeatureIds(): string[] {
    return featureRegistry.list().map((entry) => entry.id);
}

/** Clear feature ids only (tests). Does not clear nested registries. */
export function clearFeatureIds(): void {
    featureRegistry.clear();
}
