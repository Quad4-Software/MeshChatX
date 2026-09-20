// SPDX-License-Identifier: 0BSD

import { camelCaseToSearchWords } from "../settingsSearchUtils.js";

/** @typedef {{ id: string, labelKey: string, descriptionKey: string, icon: string, sections: string[] }} SettingsTab */

/** @type {SettingsTab[]} */
export const SETTINGS_TABS = [
    {
        id: "general",
        labelKey: "settings.tabs.general",
        descriptionKey: "settings.tabs.general_desc",
        icon: "cog-outline",
        sections: [
            "language",
            "translation",
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
        icon: "message-text-outline",
        sections: ["strangerProtection", "messages", "notificationSounds", "propagation", "stickers", "gifs"],
    },
    {
        id: "network",
        labelKey: "settings.tabs.network",
        descriptionKey: "settings.tabs.network_desc",
        icon: "access-point-network",
        sections: ["transport", "interfaces", "visualiser", "crawler", "networkSecurity", "telephony"],
    },
    {
        id: "nomad",
        labelKey: "settings.tabs.nomad",
        descriptionKey: "settings.tabs.nomad_desc",
        icon: "compass-outline",
        sections: ["archiver", "nomadRenderer"],
    },
    {
        id: "privacy",
        labelKey: "settings.tabs.privacy",
        descriptionKey: "settings.tabs.privacy_desc",
        icon: "shield-lock-outline",
        sections: ["privacyData", "blocked", "banishment", "auth", "webExposure", "csp"],
    },
    {
        id: "maintenance",
        labelKey: "settings.tabs.maintenance",
        descriptionKey: "settings.tabs.maintenance_desc",
        icon: "wrench-outline",
        sections: ["maintenance", "selftest", "infrastructure", "reticulumStack"],
    },
    {
        id: "plugins",
        labelKey: "settings.tabs.plugins",
        descriptionKey: "settings.tabs.plugins_desc",
        icon: "puzzle-outline",
        sections: ["plugins"],
    },
];

export const DEFAULT_SETTINGS_TAB = "general";

/**
 * Sections that only show in "Advanced" settings mode. These are technical or
 * expert-level settings; everyday sections stay visible in "Simple" mode.
 * Advanced sections always remain reachable through settings search.
 */
const ADVANCED_SETTINGS_SECTIONS = new Set([
    "translation",
    "experimentalLive",
    "transport",
    "interfaces",
    "visualiser",
    "crawler",
    "networkSecurity",
    "telephony",
    "archiver",
    "nomadRenderer",
    "banishment",
    "webExposure",
    "csp",
    "selftest",
    "infrastructure",
    "reticulumStack",
    "plugins",
]);

/**
 * @param {string} sectionKey
 * @returns {boolean}
 */
export function isAdvancedSettingsSection(sectionKey) {
    return ADVANCED_SETTINGS_SECTIONS.has(sectionKey);
}

/**
 * Sections of a tab that should render for the given mode.
 * @param {SettingsTab | null | undefined} tab
 * @param {string} mode "simple" | "advanced"
 * @returns {string[]}
 */
export function visibleSectionsForTab(tab, mode) {
    if (!tab) {
        return [];
    }
    if (mode !== "simple") {
        return tab.sections;
    }
    return tab.sections.filter((sectionKey) => !isAdvancedSettingsSection(sectionKey));
}

/**
 * Whether a tab has any section visible for the given mode.
 * @param {SettingsTab | null | undefined} tab
 * @param {string} mode
 * @returns {boolean}
 */
export function settingsTabHasVisibleSections(tab, mode) {
    return visibleSectionsForTab(tab, mode).length > 0;
}

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
