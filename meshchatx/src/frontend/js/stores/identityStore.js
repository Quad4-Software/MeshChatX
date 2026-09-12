// @ts-check

import { defineStore } from "pinia";

/**
 * Active LXMF identity and identity-scoped lists such as blocked
 * destinations. Identity switches reset this store so state never leaks
 * across identities.
 *
 * Read via useIdentityStore() in new code.
 */
export const useIdentityStore = defineStore("identity", {
    state: () => ({
        /** @type {object | null} */
        currentIdentity: null,
        /** @type {Array<any>} */
        blockedDestinations: [],
    }),
});
