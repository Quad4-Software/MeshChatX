import type { createApiClient } from "./js/apiClient.js";

declare global {
    interface Window {
        /** Shared API client instance created in main.js. */
        api: ReturnType<typeof createApiClient>;
        /** Electron preload bridge, present only in the desktop shell. */
        electron?: any;
    }
}

export {};
