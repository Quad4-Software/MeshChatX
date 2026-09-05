// SPDX-License-Identifier: 0BSD

import {
    TELEPHONE_RECORDINGS_ENDPOINT,
    TELEPHONE_VOICEMAILS_ENDPOINT,
    TELEPHONE_VOICEMAIL_GENERATE_GREETING_ENDPOINT,
    TELEPHONE_VOICEMAIL_GREETING_ENDPOINT,
    TELEPHONE_VOICEMAIL_GREETING_UPLOAD_ENDPOINT,
    TELEPHONE_VOICEMAIL_RECORD_START_ENDPOINT,
    TELEPHONE_VOICEMAIL_RECORD_STOP_ENDPOINT,
    TELEPHONE_VOICEMAIL_STATUS_ENDPOINT,
} from "./constants.js";
import type { GenerateGreetingResponse, RecordingsResponse, VoicemailStatus, VoicemailsResponse } from "./types.js";

declare const window: {
    api?: {
        get: (url: string, config?: unknown) => Promise<{ data: unknown }>;
        post: (url: string, data?: unknown, config?: unknown) => Promise<{ data: unknown }>;
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
 * Fetches voicemail service status
 */
export async function fetchVoicemailStatus(): Promise<VoicemailStatus> {
    const api = getApiClient();
    const response = await api.get(TELEPHONE_VOICEMAIL_STATUS_ENDPOINT);
    return response.data as VoicemailStatus;
}

/**
 * Starts recording greeting audio from local microphone
 */
export async function startRecordingGreetingMic(): Promise<{ message?: string }> {
    const api = getApiClient();
    const response = await api.post(TELEPHONE_VOICEMAIL_RECORD_START_ENDPOINT);
    return response.data as { message?: string };
}

/**
 * Stops recording greeting audio from local microphone
 */
export async function stopRecordingGreetingMic(): Promise<{ message?: string }> {
    const api = getApiClient();
    const response = await api.post(TELEPHONE_VOICEMAIL_RECORD_STOP_ENDPOINT);
    return response.data as { message?: string };
}

/**
 * Fetches voicemails list
 */
export async function fetchVoicemails(
    options: {
        search?: string;
        limit?: number;
        offset?: number;
    } = {}
): Promise<VoicemailsResponse> {
    const api = getApiClient();
    const params: Record<string, unknown> = {};
    if (options.search) params.search = options.search;
    if (options.limit !== undefined) params.limit = options.limit;
    if (options.offset !== undefined) params.offset = options.offset;
    const response = await api.get(TELEPHONE_VOICEMAILS_ENDPOINT, { params });
    return response.data as VoicemailsResponse;
}

/**
 * Marks a voicemail as read
 */
export async function markVoicemailAsRead(voicemailId: number | string): Promise<{ message?: string }> {
    const api = getApiClient();
    const cleanId = encodeURIComponent(String(voicemailId));
    const response = await api.post(`${TELEPHONE_VOICEMAILS_ENDPOINT}/${cleanId}/read`);
    return response.data as { message?: string };
}

/**
 * Deletes a voicemail record
 */
export async function deleteVoicemail(voicemailId: number | string): Promise<{ message?: string }> {
    const api = getApiClient();
    const cleanId = encodeURIComponent(String(voicemailId));
    const response = await api.delete(`${TELEPHONE_VOICEMAILS_ENDPOINT}/${cleanId}`);
    return response.data as { message?: string };
}

/**
 * Generates voicemail greeting audio using text to speech
 */
export async function generateVoicemailGreeting(data?: Record<string, unknown>): Promise<GenerateGreetingResponse> {
    const api = getApiClient();
    const response = await api.post(TELEPHONE_VOICEMAIL_GENERATE_GREETING_ENDPOINT, data);
    return response.data as GenerateGreetingResponse;
}

/**
 * Uploads a custom greeting audio file
 */
export async function uploadVoicemailGreeting(
    fileOrFormData: File | FormData
): Promise<{ message?: string; path?: string }> {
    const api = getApiClient();
    const formData =
        fileOrFormData instanceof FormData
            ? fileOrFormData
            : (() => {
                  const fd = new FormData();
                  fd.append("audio_file", fileOrFormData);
                  return fd;
              })();
    const response = await api.post(TELEPHONE_VOICEMAIL_GREETING_UPLOAD_ENDPOINT, formData, {
        headers: { "Content-Type": "multipart/form-data" },
    });
    return response.data as { message?: string; path?: string };
}

/**
 * Deletes the custom voicemail greeting
 */
export async function deleteVoicemailGreeting(): Promise<{ message?: string }> {
    const api = getApiClient();
    const response = await api.delete(TELEPHONE_VOICEMAIL_GREETING_ENDPOINT);
    return response.data as { message?: string };
}

/**
 * Fetches call recordings list
 */
export async function fetchRecordings(
    options: {
        search?: string;
        limit?: number;
        offset?: number;
    } = {}
): Promise<RecordingsResponse> {
    const api = getApiClient();
    const params: Record<string, unknown> = {};
    if (options.search) params.search = options.search;
    if (options.limit !== undefined) params.limit = options.limit;
    if (options.offset !== undefined) params.offset = options.offset;
    const response = await api.get(TELEPHONE_RECORDINGS_ENDPOINT, { params });
    return response.data as RecordingsResponse;
}

/**
 * Deletes a call recording
 */
export async function deleteRecording(recordingId: number | string): Promise<{ message?: string }> {
    const api = getApiClient();
    const cleanId = encodeURIComponent(String(recordingId));
    const response = await api.delete(`${TELEPHONE_RECORDINGS_ENDPOINT}/${cleanId}`);
    return response.data as { message?: string };
}
