// SPDX-License-Identifier: 0BSD

import GlobalState, { subscribeGlobalState } from "./GlobalState";

/**
 * True when DB-backed HTTP is expected to answer (or startup gave up).
 * Early ui_ready mounts can run while networkStarting and identity setup
 * still return 503 for folder/contact/conversation reads.
 */
export function isIdentityHttpReady(): boolean {
    if (GlobalState.networkReady || GlobalState.networkDegraded) {
        return true;
    }
    return !GlobalState.networkStarting;
}

/**
 * Run callback once identity HTTP is usable. Returns an optional stop fn.
 */
export function runWhenIdentityHttpReady(callback: () => void): (() => void) | null {
    if (typeof callback !== "function") {
        return null;
    }
    if (isIdentityHttpReady()) {
        callback();
        return null;
    }
    const stop = subscribeGlobalState(() => {
        if (!isIdentityHttpReady()) {
            return;
        }
        stop();
        callback();
    });
    return stop;
}
