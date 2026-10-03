import { defineStore } from "pinia";

export interface NetworkState {
    networkDegraded: boolean;
    networkDegradedError: string | null;
    networkStarting: boolean;
    networkReady: boolean;
    liveTransportReady: boolean;
}

/**
 * Backend connectivity and startup phase state.
 */
export const useNetworkStore = defineStore("network", {
    state: (): NetworkState => ({
        networkDegraded: false,
        networkDegradedError: null,
        networkStarting: false,
        networkReady: true,
        liveTransportReady: false,
    }),
});
