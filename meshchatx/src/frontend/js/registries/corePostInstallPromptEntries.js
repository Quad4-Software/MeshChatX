// SPDX-License-Identifier: 0BSD

/**
 * Core post-install / existing-user prompts.
 *
 * To re-prompt users who already dismissed a prompt, bump `revision`.
 * Add entries here and register them via registerCoreContributions.
 *
 * @type {import('./postInstallPromptRegistry.js').PostInstallPromptEntry[]}
 */
export const CORE_POST_INSTALL_PROMPT_ENTRIES = [
    // Example:
    // {
    //     id: "example_notice",
    //     revision: 1,
    //     priority: 10,
    //     titleKey: "post_install.example_title",
    //     descriptionKey: "post_install.example_desc",
    //     primaryLabelKey: "common.got_it",
    // },
];
