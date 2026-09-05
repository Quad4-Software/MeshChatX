// SPDX-License-Identifier: 0BSD

import { camelCaseToSearchWords } from "../settingsSearchUtils.js";

/** @typedef {{ id: string, labelKey: string, descriptionKey: string, sections: string[] }} SettingsTab */

/** @type {SettingsTab[]} */
export const SETTINGS_TABS = [
    {
        id: "general",
        labelKey: "settings.tabs.general",
        descriptionKey: "settings.tabs.general_desc",
        sections: [
            "language",
            "appearance",
            "battery",
            "experimentalLive",
            "desktop",
            "android",
            "shortcuts",
            "location",
        ],
    },
    {
        id: "messages",
        labelKey: "settings.tabs.messages",
        descriptionKey: "settings.tabs.messages_desc",
        sections: ["strangerProtection", "messages", "notificationSounds", "propagation", "stickers", "gifs"],
    },
    {
        id: "network",
        labelKey: "settings.tabs.network",
        descriptionKey: "settings.tabs.network_desc",
        sections: ["transport", "interfaces", "visualiser", "crawler", "networkSecurity", "telephony"],
    },
    {
        id: "nomad",
        labelKey: "settings.tabs.nomad",
        descriptionKey: "settings.tabs.nomad_desc",
        sections: ["archiver", "nomadRenderer"],
    },
    {
        id: "privacy",
        labelKey: "settings.tabs.privacy",
        descriptionKey: "settings.tabs.privacy_desc",
        sections: ["privacyData", "blocked", "banishment", "auth", "webExposure", "csp"],
    },
    {
        id: "maintenance",
        labelKey: "settings.tabs.maintenance",
        descriptionKey: "settings.tabs.maintenance_desc",
        sections: ["maintenance", "selftest", "infrastructure"],
    },
    {
        id: "plugins",
        labelKey: "settings.tabs.plugins",
        descriptionKey: "settings.tabs.plugins_desc",
        sections: ["plugins"],
    },
];

export const DEFAULT_SETTINGS_TAB = "general";

/** @type {readonly string[]} */
export const ALL_SETTINGS_SECTIONS = Object.freeze(SETTINGS_TABS.flatMap((tab) => tab.sections));

/**
 * @param {string | undefined | null} tabId
 * @returns {SettingsTab | null}
 */
export function getSettingsTab(tabId) {
    if (!tabId) {
        return null;
    }
    return SETTINGS_TABS.find((tab) => tab.id === tabId) ?? null;
}

/**
 * @param {string | undefined | null} tabId
 * @returns {string}
 */
export function normalizeSettingsTabId(tabId) {
    const normalized = typeof tabId === "string" ? tabId.trim() : "";
    if (normalized && SETTINGS_TABS.some((tab) => tab.id === normalized)) {
        return normalized;
    }
    return DEFAULT_SETTINGS_TAB;
}

/**
 * @param {string} sectionKey
 * @returns {string | null}
 */
export function settingsTabForSection(sectionKey) {
    const tab = SETTINGS_TABS.find((entry) => entry.sections.includes(sectionKey));
    return tab ? tab.id : null;
}

/**
 * @param {string} sectionKey
 * @param {string} tabId
 * @returns {boolean}
 */
export function settingsSectionBelongsToTab(sectionKey, tabId) {
    const tab = getSettingsTab(tabId);
    return Boolean(tab && tab.sections.includes(sectionKey));
}

/**
 * Extra search texts for a section: parent tab label plus the section id as words.
 * Tab descriptions are omitted because they are full of generic words (maps, security).
 *
 * @param {string} sectionKey
 * @returns {string[]}
 */
export function settingsSectionSearchExtras(sectionKey) {
    const extras = [];
    const tab = SETTINGS_TABS.find((entry) => entry.sections.includes(sectionKey));
    if (tab) {
        extras.push(tab.labelKey);
    }
    const words = camelCaseToSearchWords(sectionKey);
    if (words) {
        extras.push(`=${words}`);
    }
    return extras;
}
