// SPDX-License-Identifier: 0BSD

/**
 * Framework-free subscription adapter over GlobalState.
 * Vue keeps using the reactive object. Svelte and plain JS use this API.
 */

/** @type {Set<(snapshot: object) => void>} */
const listeners = new Set();

/**
 * @returns {object}
 */
function readSnapshot(globalState) {
    return globalState;
}

/**
 * Notify subscribers after an external mutation of GlobalState.
 * Call from code that patches state outside Vue's reactive tracking when needed.
 * @param {object} globalState
 */
export function notifyAppStateListeners(globalState) {
    const snapshot = readSnapshot(globalState);
    for (const listener of listeners) {
        try {
            listener(snapshot);
        } catch (err) {
            console.error("appState listener failed", err);
        }
    }
}

/**
 * @param {object} globalState
 * @param {(snapshot: object) => void} listener
 * @returns {() => void} unsubscribe
 */
export function subscribeAppState(globalState, listener) {
    if (typeof listener !== "function") {
        throw new Error("subscribeAppState: listener must be a function");
    }
    listeners.add(listener);
    listener(readSnapshot(globalState));
    return () => {
        listeners.delete(listener);
    };
}

/**
 * @param {object} globalState
 * @returns {object}
 */
export function getAppState(globalState) {
    return readSnapshot(globalState);
}

/**
 * Shallow-assign keys onto GlobalState and notify listeners.
 * @param {object} globalState
 * @param {Record<string, unknown>} patch
 */
export function patchAppState(globalState, patch) {
    if (!patch || typeof patch !== "object") {
        return;
    }
    Object.assign(globalState, patch);
    notifyAppStateListeners(globalState);
}

/**
 * Merge into globalState.config and notify.
 * @param {object} globalState
 * @param {Record<string, unknown>} next
 */
export function patchAppConfig(globalState, next) {
    if (!next || typeof next !== "object") {
        return;
    }
    const prev = globalState.config && typeof globalState.config === "object" ? globalState.config : {};
    globalState.config = { ...prev, ...next };
    notifyAppStateListeners(globalState);
}
