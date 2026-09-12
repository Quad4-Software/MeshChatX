// @ts-check

import { defineStore } from "pinia";

/**
 * Backend connectivity and startup phase state.
 *
 * Read via useNetworkStore() in new code.
 */
export const useNetworkStore = defineStore("network", {
    state: () => ({
        networkDegraded: false,
        /** @type {string | null} */
        networkDegradedError: null,
        networkStarting: false,
        networkReady: true,
        liveTransportReady: false,
    }),
});
