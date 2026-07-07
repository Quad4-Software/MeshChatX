// SPDX-License-Identifier: 0BSD

import { createRegistry } from "./registryCore.js";

/**
 * @typedef {Object} SettingsSectionEntry
 * @property {string} id
 * @property {string[]} keywords
 * @property {import('vue').Component | null} [component]
 * @property {string | null} [pluginId]
 */

/** @type {import('./registryCore.js').Registry<SettingsSectionEntry>} */
export const settingsSectionRegistry = createRegistry("settingsSectionRegistry");

/**
 * @param {Omit<SettingsSectionEntry, 'id'> & { id: string }} entry
 */
export function registerSettingsSection(entry) {
    settingsSectionRegistry.register(entry);
}

/**
 * @param {string} id
 */
export function unregisterSettingsSection(id) {
    settingsSectionRegistry.unregister(id);
}

/**
 * @returns {SettingsSectionEntry[]}
 */
export function listSettingsSections() {
    return settingsSectionRegistry.list();
}

/**
 * @param {string} sectionKey
 * @returns {string[] | undefined}
 */
export function getSettingsSectionKeywords(sectionKey) {
    return settingsSectionRegistry.get(sectionKey)?.keywords;
}

/**
 * @returns {Record<string, string[]>}
 */
export function getAllSettingsSectionKeywords() {
    /** @type {Record<string, string[]>} */
    const map = {};
    for (const entry of settingsSectionRegistry.list()) {
        map[entry.id] = entry.keywords;
    }
    return map;
}

/**
 * @param {string} sectionKey
 * @returns {import('vue').Component | null | undefined}
 */
export function getSettingsSectionComponent(sectionKey) {
    return settingsSectionRegistry.get(sectionKey)?.component;
}
