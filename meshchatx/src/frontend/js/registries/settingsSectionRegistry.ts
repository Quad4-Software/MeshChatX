// SPDX-License-Identifier: 0BSD

import type { Component } from "vue";
import { createRegistry } from "./registryCore";

export interface SettingsSectionEntry {
    id: string;
    keywords: string[];
    component?: Component | null;
    pluginId?: string | null;
}

export const settingsSectionRegistry = createRegistry<SettingsSectionEntry>("settingsSectionRegistry");

export function registerSettingsSection(entry: SettingsSectionEntry): void {
    settingsSectionRegistry.register(entry);
}

export function unregisterSettingsSection(id: string): void {
    settingsSectionRegistry.unregister(id);
}

export function listSettingsSections(): SettingsSectionEntry[] {
    return settingsSectionRegistry.list();
}

export function getSettingsSectionKeywords(sectionKey: string): string[] | undefined {
    return settingsSectionRegistry.get(sectionKey)?.keywords;
}

export function getAllSettingsSectionKeywords(): Record<string, string[]> {
    const map: Record<string, string[]> = {};
    for (const entry of settingsSectionRegistry.list()) {
        map[entry.id] = entry.keywords;
    }
    return map;
}

export function getSettingsSectionComponent(sectionKey: string): Component | null | undefined {
    return settingsSectionRegistry.get(sectionKey)?.component;
}
