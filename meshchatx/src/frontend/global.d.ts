import type { createApiClient } from "./js/apiClient.js";

declare global {
    interface Window {
        /** Shared API client instance created in main.js. */
        api: ReturnType<typeof createApiClient>;
    }
}

export {};
