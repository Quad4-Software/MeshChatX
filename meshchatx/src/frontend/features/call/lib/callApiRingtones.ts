// SPDX-License-Identifier: 0BSD

import {
    TELEPHONE_RINGTONES_ENDPOINT,
    TELEPHONE_RINGTONES_STATUS_ENDPOINT,
    TELEPHONE_RINGTONES_UPLOAD_ENDPOINT,
} from "./constants.js";
import type {
    Ringtone,
    RingtoneStatus,
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
 * Fetches all ringtones
 */
export async function fetchRingtones(): Promise<Ringtone[]> {
    const api = getApiClient();
    const response = await api.get(TELEPHONE_RINGTONES_ENDPOINT);
    return response.data as Ringtone[];
}

/**
 * Fetches active ringtone status
 */
export async function fetchRingtoneStatus(callerHash?: string): Promise<RingtoneStatus> {
    const api = getApiClient();
    const params = callerHash ? { caller_hash: callerHash } : undefined;
    const response = await api.get(TELEPHONE_RINGTONES_STATUS_ENDPOINT, { params });
    return response.data as RingtoneStatus;
}

/**
 * Updates ringtone metadata or sets it as primary
 */
export async function patchRingtone(
    ringtoneId: number | string,
    patch: { is_primary?: boolean; display_name?: string }
): Promise<{ message?: string }> {
    const api = getApiClient();
    const cleanId = encodeURIComponent(String(ringtoneId));
    const response = await api.patch(`${TELEPHONE_RINGTONES_ENDPOINT}/${cleanId}`, patch);
    return response.data as { message?: string };
}

/**
 * Deletes a ringtone file and record
 */
export async function deleteRingtone(ringtoneId: number | string): Promise<{ message?: string }> {
    const api = getApiClient();
    const cleanId = encodeURIComponent(String(ringtoneId));
    const response = await api.delete(`${TELEPHONE_RINGTONES_ENDPOINT}/${cleanId}`);
    return response.data as { message?: string };
}

/**
 * Uploads a ringtone audio file
 */
export async function uploadRingtone(formData: FormData): Promise<{ message?: string }> {
    const api = getApiClient();
    const response = await api.post(TELEPHONE_RINGTONES_UPLOAD_ENDPOINT, formData, {
        headers: { "Content-Type": "multipart/form-data" },
    });
    return response.data as { message?: string };
}
