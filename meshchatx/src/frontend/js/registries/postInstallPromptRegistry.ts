// SPDX-License-Identifier: 0BSD

import { createRegistry } from "./registryCore.js";

export interface PostInstallPromptEntry {
    id: string;
    revision: number;
    titleKey: string;
    descriptionKey?: string;
    primaryLabelKey?: string;
    secondaryLabelKey?: string;
    priority?: number;
    shouldShow?: () => boolean | Promise<boolean>;
    onPrimary?: (ctx: { entry: PostInstallPromptEntry }) => boolean | void | Promise<boolean | void>;
    onSecondary?: (ctx: { entry: PostInstallPromptEntry }) => boolean | void | Promise<boolean | void>;
    dismissOnPrimary?: boolean;
    dismissOnSecondary?: boolean;
}

export const postInstallPromptRegistry = createRegistry<PostInstallPromptEntry>("postInstallPromptRegistry");

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
