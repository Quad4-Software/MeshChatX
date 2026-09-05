// SPDX-License-Identifier: 0BSD

import { watch } from "vue";
import GlobalState from "./GlobalState";

/**
 * True when DB-backed HTTP is expected to answer (or startup gave up).
 * Early ui_ready mounts can run while networkStarting and identity setup
 * still return 503 for folder/contact/conversation reads.
 */
export function isIdentityHttpReady() {
    if (GlobalState.networkReady || GlobalState.networkDegraded) {
        return true;
    }
    return !GlobalState.networkStarting;
}

/**
 * Run callback once identity HTTP is usable. Returns an optional stop fn.
 * @param {() => void} callback
 * @returns {(() => void) | null}
 */
export function runWhenIdentityHttpReady(callback) {
    if (typeof callback !== "function") {
        return null;
    }
    if (isIdentityHttpReady()) {
        callback();
        return null;
    }
    const stop = watch(
        () => [GlobalState.networkReady, GlobalState.networkDegraded, GlobalState.networkStarting],
        () => {
            if (!isIdentityHttpReady()) {
                return;
            }
            stop();
            callback();
        }
    );
    return stop;
}
