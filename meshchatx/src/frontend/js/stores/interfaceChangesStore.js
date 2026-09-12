// @ts-check

import { defineStore } from "pinia";

/**
 * Pending Reticulum interface edits that require an RNS reload.
 *
 * Read via useInterfaceChangesStore() in new code.
 */
export const useInterfaceChangesStore = defineStore("interfaceChanges", {
    state: () => ({
        /** @type {Set<string>} */
        modifiedInterfaceNames: new Set(),
        hasPendingInterfaceChanges: false,
    }),
});
