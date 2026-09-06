// SPDX-License-Identifier: 0BSD

/**
 * Svelte-friendly reactive mirror of GlobalState via appState.subscribe.
 * Import from .svelte / .svelte.js modules only (not from plain kernel .ts/.js).
 */

import globalState from "../GlobalState.js";
import { subscribeAppState, getAppState, patchAppState, patchAppConfig, type AppStateSnapshot } from "../appState.js";

export const appState: AppStateSnapshot = $state({ ...getAppState(globalState as AppStateSnapshot) });

subscribeAppState(globalState as AppStateSnapshot, (snapshot) => {
    Object.assign(appState, snapshot);
    if (snapshot.config && typeof snapshot.config === "object") {
        appState.config = { ...snapshot.config };
    }
});

export function patchState(patch: Record<string, unknown>): void {
    patchAppState(globalState as AppStateSnapshot, patch);
}

export function patchConfig(next: Record<string, unknown>): void {
    patchAppConfig(globalState as AppStateSnapshot, next);
}
