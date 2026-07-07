// SPDX-License-Identifier: 0BSD

import { CORE_NAV_ENTRIES } from "./coreNavEntries.js";
import { registerNavItem } from "./navRegistry.js";
import { CORE_TOOLS_ENTRIES } from "./coreToolsEntries.js";
import { registerTool } from "./toolsRegistry.js";
import { CORE_COMMAND_ENTRIES } from "./coreCommandEntries.js";
import { registerCommand } from "./commandRegistry.js";
import { CORE_SETTINGS_SECTION_KEYWORDS } from "./coreSettingsSectionKeywords.js";
import { registerSettingsSection } from "./settingsSectionRegistry.js";

let coreRegistered = false;

export function resetCoreContributionsForTests() {
    coreRegistered = false;
}

export function registerCoreContributions() {
    if (coreRegistered) {
        return;
    }
    coreRegistered = true;

    for (const entry of CORE_NAV_ENTRIES) {
        registerNavItem(entry);
    }

    for (const entry of CORE_TOOLS_ENTRIES) {
        registerTool(entry);
    }

    for (const entry of CORE_COMMAND_ENTRIES) {
        registerCommand(entry);
    }

    for (const [sectionId, keywords] of Object.entries(CORE_SETTINGS_SECTION_KEYWORDS)) {
        registerSettingsSection({ id: sectionId, keywords });
    }
}
