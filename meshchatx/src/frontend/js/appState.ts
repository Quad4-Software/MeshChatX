// SPDX-License-Identifier: 0BSD

/**
 * Framework-free subscription adapter over GlobalState.
 * Svelte and plain JS subscribe here. GlobalState itself notifies via Proxy.
 */

export type AppStateSnapshot = {
    config?: Record<string, unknown> | null;
    [key: string]: unknown;
};

export type AppStateListener = (snapshot: AppStateSnapshot) => void;

const listeners = new Set<AppStateListener>();

function readSnapshot(globalState: AppStateSnapshot): AppStateSnapshot {
    return globalState;
}

/**
 * Notify subscribers after an external mutation of GlobalState.
 * Call from code that patches state when the Proxy setter did not already notify.
 */
export function notifyAppStateListeners(globalState: AppStateSnapshot): void {
    const snapshot = readSnapshot(globalState);
    for (const listener of listeners) {
        try {
            listener(snapshot);
        } catch (err) {
            console.error("appState listener failed", err);
        }
    }
}

export function subscribeAppState(globalState: AppStateSnapshot, listener: AppStateListener): () => void {
    if (typeof listener !== "function") {
        throw new Error("subscribeAppState: listener must be a function");
    }
    listeners.add(listener);
    listener(readSnapshot(globalState));
    return () => {
        listeners.delete(listener);
    };
}

export function getAppState(globalState: AppStateSnapshot): AppStateSnapshot {
    return readSnapshot(globalState);
}

/** Shallow-assign keys onto GlobalState and notify listeners. */
export function patchAppState(globalState: AppStateSnapshot, patch: Record<string, unknown>): void {
    if (!patch || typeof patch !== "object") {
        return;
    }
    Object.assign(globalState, patch);
    notifyAppStateListeners(globalState);
}

/** Merge into globalState.config and notify. */
export function patchAppConfig(globalState: AppStateSnapshot, next: Record<string, unknown>): void {
    if (!next || typeof next !== "object") {
        return;
    }
    const prev = globalState.config && typeof globalState.config === "object" ? globalState.config : {};
    globalState.config = { ...prev, ...next };
    notifyAppStateListeners(globalState);
}
