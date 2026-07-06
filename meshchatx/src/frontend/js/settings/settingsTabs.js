// SPDX-License-Identifier: 0BSD

/** @typedef {{ id: string, labelKey: string, descriptionKey: string, sections: string[] }} SettingsTab */

/** @type {SettingsTab[]} */
export const SETTINGS_TABS = [
    {
        id: "general",
        labelKey: "settings.tabs.general",
        descriptionKey: "settings.tabs.general_desc",
        sections: ["language", "appearance", "desktop", "android", "shortcuts"],
    },
    {
        id: "messages",
        labelKey: "settings.tabs.messages",
        descriptionKey: "settings.tabs.messages_desc",
        sections: ["strangerProtection", "messages", "propagation", "stickers", "gifs", "banishment", "telephony"],
    },
    {
        id: "network",
        labelKey: "settings.tabs.network",
        descriptionKey: "settings.tabs.network_desc",
        sections: ["transport", "interfaces", "visualiser", "location", "crawler", "infrastructure", "networkSecurity"],
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
        sections: ["privacyData", "blocked", "auth", "webExposure", "csp"],
    },
    {
        id: "maintenance",
        labelKey: "settings.tabs.maintenance",
        descriptionKey: "settings.tabs.maintenance_desc",
        sections: ["maintenance"],
    },
];

export const DEFAULT_SETTINGS_TAB = "general";

/**
 * @param {string | undefined | null} tabId
 * @returns {string}
 */
export function normalizeSettingsTabId(tabId) {
    if (tabId && SETTINGS_TABS.some((tab) => tab.id === tabId)) {
        return tabId;
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
