// SPDX-License-Identifier: 0BSD

import { camelCaseToSearchWords } from "../settingsSearchUtils.js";

export type SettingsTab = {
    id: string;
    labelKey: string;
    descriptionKey: string;
    sections: string[];
};

export const SETTINGS_TABS: SettingsTab[] = [
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

export const ALL_SETTINGS_SECTIONS: readonly string[] = Object.freeze(SETTINGS_TABS.flatMap((tab) => tab.sections));

export function getSettingsTab(tabId: string | undefined | null): SettingsTab | null {
    if (!tabId) {
        return null;
    }
    return SETTINGS_TABS.find((tab) => tab.id === tabId) ?? null;
}

export function normalizeSettingsTabId(tabId: string | undefined | null): string {
    const normalized = typeof tabId === "string" ? tabId.trim() : "";
    if (normalized && SETTINGS_TABS.some((tab) => tab.id === normalized)) {
        return normalized;
    }
    return DEFAULT_SETTINGS_TAB;
}

export function settingsTabForSection(sectionKey: string): string | null {
    const tab = SETTINGS_TABS.find((entry) => entry.sections.includes(sectionKey));
    return tab ? tab.id : null;
}

export function settingsSectionBelongsToTab(sectionKey: string, tabId: string): boolean {
    const tab = getSettingsTab(tabId);
    return Boolean(tab && tab.sections.includes(sectionKey));
}

/**
 * Extra search texts for a section: parent tab label plus the section id as words.
 * Tab descriptions are omitted because they are full of generic words (maps, security).
 */
export function settingsSectionSearchExtras(sectionKey: string): string[] {
    const extras: string[] = [];
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
