import { defineStore } from "pinia";

/** A 16-byte LXMF destination hash, hex-encoded. */
export type DestinationHash = string;

/**
 * The currently active LXMF identity as returned by the backend.
 */
export interface Identity {
    hash: DestinationHash;
    display_name: string | null;
    lxmf_address: string | null;
    lxst_address: string | null;
    message_count: number | null;
    icon_name: string | null;
    icon_background_colour: string | null;
    icon_foreground_colour: string | null;
    is_current?: boolean;
    is_node?: boolean;
    is_rns_blackholed?: boolean;
    [key: string]: unknown;
}

/** A blocked destination entry. */
export interface BlockedDestination {
    destination_hash: DestinationHash;
    [key: string]: unknown;
}

export interface IdentityState {
    currentIdentity: Identity | null;
    blockedDestinations: BlockedDestination[];
}

/**
 * Active LXMF identity and identity-scoped lists such as blocked
 * destinations. Identity switches reset this store so state never leaks
 * across identities.
 */
export const useIdentityStore = defineStore("identity", {
    state: (): IdentityState => ({
        currentIdentity: null,
        blockedDestinations: [],
    }),
});
