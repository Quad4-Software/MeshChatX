// SPDX-License-Identifier: 0BSD

import { createRegistry } from "./registryCore.js";

export interface SettingsSectionEntry {
    id: string;
    keywords?: string[];
    component?: any;
    pluginId?: string | null;
}

export const settingsSectionRegistry = createRegistry<SettingsSectionEntry>("settingsSectionRegistry");

export function registerSettingsSection(entry: SettingsSectionEntry) {
    settingsSectionRegistry.register(entry);
}

export function unregisterSettingsSection(id: string) {
    settingsSectionRegistry.unregister(id);
}

export function listSettingsSections(): SettingsSectionEntry[] {
    return settingsSectionRegistry.list();
}

export function getSettingsSectionKeywords(sectionKey: string): string[] | undefined {
    return settingsSectionRegistry.get(sectionKey)?.keywords;
}

export function getAllSettingsSectionKeywords(): Record<string, string[] | undefined> {
    const map: Record<string, string[] | undefined> = {};
    for (const entry of settingsSectionRegistry.list()) {
        map[entry.id] = entry.keywords;
    }
    return map;
}

export function getSettingsSectionComponent(sectionKey: string): any {
    return settingsSectionRegistry.get(sectionKey)?.component;
}
