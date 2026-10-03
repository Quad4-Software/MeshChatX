import { defineStore } from "pinia";

export interface AuthState {
    authSessionResolved: boolean;
    authEnabled: boolean;
    isLoopbackBind: boolean;
    authenticated: boolean;
    demoMode: boolean;
    pluginsEnabled: boolean;
}

/**
 * Session and authentication state for the app shell.
 */
export const useAuthStore = defineStore("auth", {
    state: (): AuthState => ({
        authSessionResolved: false,
        authEnabled: false,
        isLoopbackBind: true,
        authenticated: false,
        demoMode: false,
        pluginsEnabled: true,
    }),
});
