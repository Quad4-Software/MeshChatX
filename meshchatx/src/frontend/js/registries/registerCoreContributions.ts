// SPDX-License-Identifier: 0BSD

import { CORE_NAV_ENTRIES } from "./coreNavEntries";
import { registerNavItem } from "./navRegistry";
import { CORE_TOOLS_ENTRIES } from "./coreToolsEntries";
import { registerTool } from "./toolsRegistry";
import { CORE_COMMAND_ENTRIES } from "./coreCommandEntries";
import { registerCommand } from "./commandRegistry";
import { CORE_SETTINGS_SECTION_KEYWORDS } from "./coreSettingsSectionKeywords";
import { registerSettingsSection } from "./settingsSectionRegistry";
import { CORE_POST_INSTALL_PROMPT_ENTRIES } from "./corePostInstallPromptEntries";
import { registerPostInstallPrompt } from "./postInstallPromptRegistry";

let coreRegistered = false;

export function resetCoreContributionsForTests(): void {
    coreRegistered = false;
}

export function registerCoreContributions(): void {
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

    for (const entry of CORE_POST_INSTALL_PROMPT_ENTRIES) {
        registerPostInstallPrompt(entry);
    }
}
