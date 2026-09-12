// @ts-check

import { defineStore } from "pinia";

/**
 * Session and authentication state for the app shell.
 *
 * Read via useAuthStore() in new code.
 */
export const useAuthStore = defineStore("auth", {
    state: () => ({
        authSessionResolved: false,
        authEnabled: false,
        isLoopbackBind: true,
        authenticated: false,
        demoMode: false,
        pluginsEnabled: true,
    }),
});
