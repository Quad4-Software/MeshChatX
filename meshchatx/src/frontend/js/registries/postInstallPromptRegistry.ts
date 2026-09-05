// SPDX-License-Identifier: 0BSD

import { createRegistry } from "./registryCore.js";

/**
 * @typedef {Object} PostInstallPromptEntry
 * @property {string} id
 * Stable prompt id. Do not rename casually.
 * @property {number} revision
 * Monotonic. Bump to re-prompt users who dismissed an older revision.
 * @property {string} titleKey
 * i18n key for the dialog title.
 * @property {string} [descriptionKey]
 * i18n key for the body text.
 * @property {string} [primaryLabelKey]
 * i18n key for the primary button. Defaults to common.continue.
 * @property {string} [secondaryLabelKey]
 * i18n key for the secondary button. Omit for primary-only.
 * @property {number} [priority]
 * Higher runs first among pending prompts. Default 0.
 * @property {() => boolean | Promise<boolean>} [shouldShow]
 * Extra gate after revision check. Return false to skip.
 * @property {(ctx: { entry: PostInstallPromptEntry }) => boolean | void | Promise<boolean | void>} [onPrimary]
 * Return false to keep the dialog open and skip dismiss.
 * @property {(ctx: { entry: PostInstallPromptEntry }) => boolean | void | Promise<boolean | void>} [onSecondary]
 * Return false to keep the dialog open and skip dismiss.
 * @property {boolean} [dismissOnPrimary]
 * Mark seen after a successful primary action. Default true.
 * @property {boolean} [dismissOnSecondary]
 * Mark seen after a successful secondary action. Default true.
 */

/** @type {import('./registryCore.js').Registry<PostInstallPromptEntry>} */
export const postInstallPromptRegistry = createRegistry("postInstallPromptRegistry");

/**
 * @param {PostInstallPromptEntry} entry
 */
export function registerPostInstallPrompt(entry) {
    if (!entry?.id) {
        throw new Error("postInstallPromptRegistry: entry requires an id");
    }
    const revision = Number(entry.revision);
    if (!Number.isFinite(revision) || revision < 1) {
        throw new Error(`postInstallPromptRegistry: entry "${entry.id}" requires revision >= 1`);
    }
    if (!entry.titleKey) {
        throw new Error(`postInstallPromptRegistry: entry "${entry.id}" requires titleKey`);
    }
    postInstallPromptRegistry.register({
        ...entry,
        revision: Math.floor(revision),
        priority: Number.isFinite(Number(entry.priority)) ? Number(entry.priority) : 0,
        dismissOnPrimary: entry.dismissOnPrimary !== false,
        dismissOnSecondary: entry.dismissOnSecondary !== false,
    });
}

/**
 * @param {string} id
 */
export function unregisterPostInstallPrompt(id) {
    postInstallPromptRegistry.unregister(id);
}

/**
 * @returns {PostInstallPromptEntry[]}
 */
export function listPostInstallPrompts() {
    return postInstallPromptRegistry.list();
}

/**
 * Highest priority first, then id for stability.
 * @returns {PostInstallPromptEntry[]}
 */
export function listPostInstallPromptsByPriority() {
    return listPostInstallPrompts()
        .slice()
        .sort((a, b) => {
            const pa = Number(a.priority) || 0;
            const pb = Number(b.priority) || 0;
            if (pb !== pa) {
                return pb - pa;
            }
            return String(a.id).localeCompare(String(b.id));
        });
}
