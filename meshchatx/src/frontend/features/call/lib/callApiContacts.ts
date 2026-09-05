// SPDX-License-Identifier: 0BSD

import Compressor from "compressorjs";
import DialogUtils from "../../../js/DialogUtils.js";
import { t } from "../../../js/i18n.js";
import ToastUtils from "../../../js/ToastUtils.js";
import {
    ANNOUNCES_API_ENDPOINT,
    BLOCKED_DESTINATIONS_API_ENDPOINT,
    DEFAULT_DISCOVERY_LIMIT,
    TELEPHONE_CONTACTS_ENDPOINT,
    TELEPHONY_ASPECT,
} from "./constants.js";
import type { ContactsResponse, DiscoveryResponse, TelephoneContact } from "./types.js";

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
export async function fetchContacts(
    options: {
        search?: string;
        limit?: number;
        offset?: number;
    } = {}
): Promise<ContactsResponse | TelephoneContact[]> {
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
export async function fetchDiscoveryAnnounces(
    options: {
        search?: string;
        limit?: number;
        offset?: number;
        aspect?: string;
    } = {}
): Promise<DiscoveryResponse> {
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

/**
 * Compresses an image file for contact avatar
 */
export function executeCompressContactImage(file: File, onSuccess: (dataUrl: string) => void): void {
    new Compressor(file, {
        quality: 0.8,
        maxWidth: 256,
        maxHeight: 256,
        mimeType: "image/webp",
        success(blob) {
            const reader = new FileReader();
            reader.onload = () => {
                if (typeof reader.result === "string") {
                    onSuccess(reader.result);
                }
            };
            reader.readAsDataURL(blob);
        },
        error(err) {
            console.error(err);
            ToastUtils.error(t("call.failed_to_compress_image"));
        },
    });
}

/**
 * Saves a new contact or updates existing contact
 */
export async function executeSaveContact(
    paramsOrForm: {
        contactId?: number | string | null;
        name?: string;
        remoteIdentityHash?: string;
        remote_identity_hash?: string;
        preferredRingtoneId?: number | null;
        preferred_ringtone_id?: number | null;
        isTelemetryTrusted?: boolean;
        is_telemetry_trusted?: boolean | number;
        imageFile?: File | null;
        custom_image?: string | null;
        clearImage?: boolean;
        clear_image?: boolean;
    },
    editingContact?: TelephoneContact | null
): Promise<boolean> {
    const contactId = editingContact?.id ?? paramsOrForm.contactId;
    const name = paramsOrForm.name || "";
    const remoteIdentityHash = paramsOrForm.remoteIdentityHash || paramsOrForm.remote_identity_hash || "";
    const preferredRingtoneId = paramsOrForm.preferredRingtoneId ?? paramsOrForm.preferred_ringtone_id ?? null;
    const isTelemetryTrusted = Boolean(paramsOrForm.isTelemetryTrusted ?? paramsOrForm.is_telemetry_trusted);
    const clearImage = Boolean(paramsOrForm.clearImage ?? paramsOrForm.clear_image);
    const imageFile = paramsOrForm.imageFile;

    if (!name || !name.trim()) {
        ToastUtils.error(t("call.contact_name_required"));
        return false;
    }
    if (!remoteIdentityHash || !remoteIdentityHash.trim()) {
        ToastUtils.error(t("call.contact_hash_required"));
        return false;
    }

    let customImageBase64: string | null = paramsOrForm.custom_image || null;
    if (imageFile) {
        customImageBase64 = await new Promise<string | null>((resolve) => {
            new Compressor(imageFile, {
                quality: 0.8,
                maxWidth: 256,
                maxHeight: 256,
                mimeType: "image/webp",
                success(blob) {
                    const reader = new FileReader();
                    reader.onload = () => resolve(reader.result as string);
                    reader.onerror = () => resolve(null);
                    reader.readAsDataURL(blob);
                },
                error() {
                    resolve(null);
                },
            });
        });
    }

    const payload: Partial<TelephoneContact> = {
        name: name.trim(),
        remote_identity_hash: remoteIdentityHash.trim(),
        preferred_ringtone_id: preferredRingtoneId || null,
        is_telemetry_trusted: isTelemetryTrusted ? 1 : 0,
    };
    if (clearImage) {
        payload.clear_image = true;
    } else if (customImageBase64) {
        payload.custom_image = customImageBase64;
    }

    try {
        if (contactId) {
            await updateContact(contactId, payload);
            ToastUtils.success(t("call.contact_updated"));
        } else {
            await createContact(payload);
            ToastUtils.success(t("call.contact_created"));
        }
        return true;
    } catch (e: any) {
        console.error(e);
        ToastUtils.error(e?.response?.data?.message || t("call.failed_to_save_contact"));
        return false;
    }
}

/**
 * Deletes a telephone contact
 */
export async function executeDeleteContact(contactId: number | string): Promise<boolean> {
    const confirmed = await DialogUtils.confirm(t("call.delete_contact_confirm"));
    if (!confirmed) return false;
    try {
        await deleteContact(contactId);
        ToastUtils.success(t("call.contact_deleted"));
        return true;
    } catch {
        ToastUtils.error(t("call.failed_to_delete_contact"));
        return false;
    }
}
