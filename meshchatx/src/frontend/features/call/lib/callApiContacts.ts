// SPDX-License-Identifier: 0BSD

import {
    ANNOUNCES_API_ENDPOINT,
    BLOCKED_DESTINATIONS_API_ENDPOINT,
    DEFAULT_DISCOVERY_LIMIT,
    TELEPHONE_CONTACTS_ENDPOINT,
    TELEPHONY_ASPECT,
} from "./constants.js";
import type {
    ContactsResponse,
    DiscoveryResponse,
    TelephoneContact,
} from "./types.js";

declare const window: {
    api?: {
        get: (url: string, config?: unknown) => Promise<{ data: unknown }>;
        post: (url: string, data?: unknown, config?: unknown) => Promise<{ data: unknown }>;
        patch: (url: string, data?: unknown, config?: unknown) => Promise<{ data: unknown }>;
        delete: (url: string, config?: unknown) => Promise<{ data: unknown }>;
    };
};

function getApiClient() {
    if (typeof window !== "undefined" && window.api) {
        return window.api;
    }
    throw new Error("window.api is not available");
}

/**
 * Fetches telephone contacts
 */
export async function fetchContacts(options: {
    search?: string;
    limit?: number;
    offset?: number;
} = {}): Promise<ContactsResponse | TelephoneContact[]> {
    const api = getApiClient();
    const params: Record<string, unknown> = {};
    if (options.search) params.search = options.search;
    if (options.limit !== undefined) params.limit = options.limit;
    if (options.offset !== undefined) params.offset = options.offset;
    const response = await api.get(TELEPHONE_CONTACTS_ENDPOINT, { params });
    return response.data as ContactsResponse | TelephoneContact[];
}

/**
 * Creates a new telephone contact
 */
export async function createContact(contact: Partial<TelephoneContact>): Promise<{ message?: string; id?: number }> {
    const api = getApiClient();
    const response = await api.post(TELEPHONE_CONTACTS_ENDPOINT, contact);
    return response.data as { message?: string; id?: number };
}

/**
 * Updates an existing telephone contact
 */
export async function updateContact(
    contactId: number | string,
    contact: Partial<TelephoneContact>
): Promise<{ message?: string }> {
    const api = getApiClient();
    const cleanId = encodeURIComponent(String(contactId));
    const response = await api.patch(`${TELEPHONE_CONTACTS_ENDPOINT}/${cleanId}`, contact);
    return response.data as { message?: string };
}

/**
 * Deletes a telephone contact
 */
export async function deleteContact(contactId: number | string): Promise<{ message?: string }> {
    const api = getApiClient();
    const cleanId = encodeURIComponent(String(contactId));
    const response = await api.delete(`${TELEPHONE_CONTACTS_ENDPOINT}/${cleanId}`);
    return response.data as { message?: string };
}

/**
 * Fetches announces for phonebook discovery
 */
export async function fetchDiscoveryAnnounces(options: {
    search?: string;
    limit?: number;
    offset?: number;
    aspect?: string;
} = {}): Promise<DiscoveryResponse> {
    const api = getApiClient();
    const params: Record<string, unknown> = {
        aspect: options.aspect ?? TELEPHONY_ASPECT,
        limit: options.limit ?? DEFAULT_DISCOVERY_LIMIT,
        offset: options.offset ?? 0,
    };
    if (options.search) {
        params.search = options.search;
    }
    const response = await api.get(ANNOUNCES_API_ENDPOINT, { params });
    return response.data as DiscoveryResponse;
}

/**
 * Blocks or banishes an identity from calling
 */
export async function blockDestination(destinationHash: string): Promise<{ message?: string }> {
    const api = getApiClient();
    const response = await api.post(BLOCKED_DESTINATIONS_API_ENDPOINT, {
        destination_hash: destinationHash,
    });
    return response.data as { message?: string };
}
