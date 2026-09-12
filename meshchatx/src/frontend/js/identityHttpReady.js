// SPDX-License-Identifier: 0BSD AND MIT

import { watch } from "vue";
import { useNetworkStore } from "./stores/networkStore.js";

/**
 * True when DB-backed HTTP is expected to answer (or startup gave up).
 * Early ui_ready mounts can run while networkStarting and identity setup
 * still return 503 for folder/contact/conversation reads.
 */
export function isIdentityHttpReady() {
    const networkStore = useNetworkStore();
    if (networkStore.networkReady || networkStore.networkDegraded) {
        return true;
    }
    return !networkStore.networkStarting;
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
    const networkStore = useNetworkStore();
    const stop = watch(
        () => [networkStore.networkReady, networkStore.networkDegraded, networkStore.networkStarting],
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
