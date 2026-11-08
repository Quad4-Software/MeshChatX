// SPDX-License-Identifier: 0BSD

import DesktopUtils from "../DesktopUtils.js";

/**
 * Core post-install / existing-user prompts.
 *
 * To re-prompt users who already dismissed a prompt, bump revision.
 * Add entries here and register them via registerCoreContributions.
 *
 * @type {import('./postInstallPromptRegistry.js').PostInstallPromptEntry[]}
 */
export const CORE_POST_INSTALL_PROMPT_ENTRIES = [
    {
        id: "windows_screen_security",
        revision: 1,
        priority: 40,
        titleKey: "post_install.windows_screen_security_title",
        descriptionKey: "post_install.windows_screen_security_desc",
        primaryLabelKey: "post_install.windows_screen_security_enable",
        secondaryLabelKey: "post_install.windows_screen_security_later",
        async shouldShow() {
            if (typeof DesktopUtils.isWindowsDesktop !== "function" || !DesktopUtils.isWindowsDesktop()) {
                return false;
            }
            try {
                const settings = await DesktopUtils.getScreenSecuritySettings();
                if (!settings?.available) {
                    return false;
                }
                return settings.enabled !== true;
            } catch {
                return false;
            }
        },
        async onPrimary() {
            try {
                await DesktopUtils.setScreenSecurityEnabled(true);
                return true;
            } catch (e) {
                console.error("Failed to enable Windows screen security:", e);
                return false;
            }
        },
    },
];
