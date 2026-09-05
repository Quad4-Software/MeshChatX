// SPDX-License-Identifier: 0BSD

/**
 * Svelte-friendly reactive mirror of GlobalState via appState.subscribe.
 * Import from .svelte / .svelte.js modules only (not from kernel consumers that must stay Vue-free of runes).
 */

import globalState from "../GlobalState.js";
import { subscribeAppState, getAppState, patchAppState, patchAppConfig } from "../appState.js";

/** @type {object} */
export const appState = $state({ ...getAppState(globalState) });

subscribeAppState(globalState, (snapshot) => {
    Object.assign(appState, snapshot);
    if (snapshot.config && typeof snapshot.config === "object") {
        appState.config = { ...snapshot.config };
    }
});

/**
 * @param {Record<string, unknown>} patch
 */
export function patchState(patch) {
    patchAppState(globalState, patch);
}

/**
 * @param {Record<string, unknown>} next
 */
export function patchConfig(next) {
    patchAppConfig(globalState, next);
}
