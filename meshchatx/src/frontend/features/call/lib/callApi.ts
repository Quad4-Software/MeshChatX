// SPDX-License-Identifier: 0BSD

import {
    CONFIG_API_ENDPOINT,
    DEFAULT_CALL_HISTORY_LIMIT,
    TELEPHONE_ANSWER_ENDPOINT,
    TELEPHONE_AUDIO_PROFILES_ENDPOINT,
    TELEPHONE_CALL_ENDPOINT,
    TELEPHONE_CALL_MODES_ENDPOINT,
    TELEPHONE_CODEC2_STATUS_ENDPOINT,
    TELEPHONE_HANGUP_ENDPOINT,
    TELEPHONE_HISTORY_ENDPOINT,
    TELEPHONE_MISSED_CALLS_MARK_VIEWED_ENDPOINT,
    TELEPHONE_MUTE_RECEIVE_ENDPOINT,
    TELEPHONE_MUTE_TRANSMIT_ENDPOINT,
    TELEPHONE_PTT_ENDPOINT,
    TELEPHONE_SEND_TO_VOICEMAIL_ENDPOINT,
    TELEPHONE_STATUS_ENDPOINT,
    TELEPHONE_SWITCH_AUDIO_PROFILE_ENDPOINT,
    TELEPHONE_SWITCH_CALL_MODE_ENDPOINT,
    TELEPHONE_UNMUTE_RECEIVE_ENDPOINT,
    TELEPHONE_UNMUTE_TRANSMIT_ENDPOINT,
} from "./constants.js";
import type {
    AudioProfilesResponse,
    CallInitiationResponse,
    CallModesResponse,
    HistoryResponse,
    PttResponse,
    SwitchAudioProfileResponse,
    SwitchCallModeResponse,
    TelephoneConfig,
    TelephoneStatus,
} from "./types.js";

export * from "./callApiContacts.js";
export * from "./callApiVoicemail.js";
export * from "./callApiRingtones.js";

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
 * Fetches telephone subsystem status
 */
export async function fetchTelephoneStatus(): Promise<TelephoneStatus> {
    const api = getApiClient();
    const response = await api.get(TELEPHONE_STATUS_ENDPOINT);
    return response.data as TelephoneStatus;
}

/**
 * Initiates an outgoing call to the specified identity hash
 */
export async function initiateCall(identityHash: string): Promise<CallInitiationResponse> {
    const api = getApiClient();
    const cleanHash = encodeURIComponent(identityHash.trim());
    const response = await api.post(`${TELEPHONE_CALL_ENDPOINT}/${cleanHash}`);
    return response.data as CallInitiationResponse;
}

/**
 * Answers an incoming ringing call
 */
export async function answerCall(): Promise<{ message?: string }> {
    const api = getApiClient();
    const response = await api.post(TELEPHONE_ANSWER_ENDPOINT);
    return response.data as { message?: string };
}

/**
 * Hangs up or rejects an active or ringing call
 */
export async function hangupCall(): Promise<{ message?: string }> {
    const api = getApiClient();
    const response = await api.post(TELEPHONE_HANGUP_ENDPOINT);
    return response.data as { message?: string };
}

/**
 * Sends an incoming ringing call to voicemail
 */
export async function sendToVoicemail(): Promise<{ message?: string }> {
    const api = getApiClient();
    const response = await api.post(TELEPHONE_SEND_TO_VOICEMAIL_ENDPOINT);
    return response.data as { message?: string };
}

/**
 * Mutes local microphone transmission
 */
export async function muteTransmit(): Promise<{ message?: string }> {
    const api = getApiClient();
    const response = await api.post(TELEPHONE_MUTE_TRANSMIT_ENDPOINT);
    return response.data as { message?: string };
}

/**
 * Unmutes local microphone transmission
 */
export async function unmuteTransmit(): Promise<{ message?: string }> {
    const api = getApiClient();
    const response = await api.post(TELEPHONE_UNMUTE_TRANSMIT_ENDPOINT);
    return response.data as { message?: string };
}

/**
 * Mutes incoming speaker audio
 */
export async function muteReceive(): Promise<{ message?: string }> {
    const api = getApiClient();
    const response = await api.post(TELEPHONE_MUTE_RECEIVE_ENDPOINT);
    return response.data as { message?: string };
}

/**
 * Unmutes incoming speaker audio
 */
export async function unmuteReceive(): Promise<{ message?: string }> {
    const api = getApiClient();
    const response = await api.post(TELEPHONE_UNMUTE_RECEIVE_ENDPOINT);
    return response.data as { message?: string };
}

/**
 * Fetches available call modes
 */
export async function fetchCallModes(): Promise<CallModesResponse> {
    const api = getApiClient();
    const response = await api.get(TELEPHONE_CALL_MODES_ENDPOINT);
    return response.data as CallModesResponse;
}

/**
 * Switches the call mode to full duplex or half duplex
 */
export async function switchCallMode(modeId: number | string): Promise<SwitchCallModeResponse> {
    const api = getApiClient();
    const cleanId = encodeURIComponent(String(modeId));
    const response = await api.post(`${TELEPHONE_SWITCH_CALL_MODE_ENDPOINT}/${cleanId}`);
    return response.data as SwitchCallModeResponse;
}

/**
 * Updates half duplex push-to-talk state
 */
export async function setPttActive(active: boolean): Promise<PttResponse> {
    const api = getApiClient();
    const response = await api.post(TELEPHONE_PTT_ENDPOINT, { active: Boolean(active) });
    return response.data as PttResponse;
}

/**
 * Fetches call history entries
 */
export async function fetchCallHistory(
    options: {
        limit?: number;
        offset?: number;
        search?: string;
    } = {}
): Promise<HistoryResponse> {
    const api = getApiClient();
    const limit = options.limit ?? DEFAULT_CALL_HISTORY_LIMIT;
    const offset = options.offset ?? 0;
    const searchParam = options.search ? `&search=${encodeURIComponent(options.search)}` : "";
    const response = await api.get(`${TELEPHONE_HISTORY_ENDPOINT}?limit=${limit}&offset=${offset}${searchParam}`);
    return response.data as HistoryResponse;
}

/**
 * Clears all call history entries
 */
export async function clearCallHistory(): Promise<{ message?: string }> {
    const api = getApiClient();
    const response = await api.delete(TELEPHONE_HISTORY_ENDPOINT);
    return response.data as { message?: string };
}

/**
 * Marks missed calls as viewed
 */
export async function markMissedCallsViewed(): Promise<{ message?: string }> {
    const api = getApiClient();
    const response = await api.post(TELEPHONE_MISSED_CALLS_MARK_VIEWED_ENDPOINT);
    return response.data as { message?: string };
}

/**
 * Fetches available audio profiles
 */
export async function fetchAudioProfiles(): Promise<AudioProfilesResponse> {
    const api = getApiClient();
    const response = await api.get(TELEPHONE_AUDIO_PROFILES_ENDPOINT);
    return response.data as AudioProfilesResponse;
}

/**
 * Switches the audio profile
 */
export async function switchAudioProfile(profileId: number | string): Promise<SwitchAudioProfileResponse> {
    const api = getApiClient();
    const cleanId = encodeURIComponent(String(profileId));
    const response = await api.post(`${TELEPHONE_SWITCH_AUDIO_PROFILE_ENDPOINT}/${cleanId}`);
    return response.data as SwitchAudioProfileResponse;
}

/**
 * Probes Codec2 codec status
 */
export async function fetchCodec2Status(): Promise<{ codec2_available: boolean }> {
    const api = getApiClient();
    const response = await api.get(TELEPHONE_CODEC2_STATUS_ENDPOINT);
    return response.data as { codec2_available: boolean };
}

/**
 * Fetches application configuration slice
 */
export async function fetchConfig(): Promise<{ config: TelephoneConfig }> {
    const api = getApiClient();
    const response = await api.get(CONFIG_API_ENDPOINT);
    return response.data as { config: TelephoneConfig };
}

/**
 * Updates application configuration
 */
export async function patchConfig(config: Partial<TelephoneConfig>): Promise<{ config: TelephoneConfig }> {
    const api = getApiClient();
    const response = await api.patch(CONFIG_API_ENDPOINT, config);
    return response.data as { config: TelephoneConfig };
}
