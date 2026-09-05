// SPDX-License-Identifier: 0BSD

import {
    clearCallHistory as apiClearCallHistory,
    fetchAudioProfiles,
    fetchCallHistory,
    fetchCallModes,
    fetchConfig,
    fetchContacts,
    fetchDiscoveryAnnounces,
    fetchRecordings,
    fetchRingtones,
    fetchRingtoneStatus,
    fetchTelephoneStatus,
    fetchVoicemails,
    fetchVoicemailStatus,
    markMissedCallsViewed as apiMarkMissedCallsViewed,
} from "./callApi.js";
import { hydrateContactVisuals } from "./callHistory.js";
import {
    CALL_ENDED_RESET_TIMEOUT_MS,
    DEFAULT_CALL_HISTORY_LIMIT,
    DEFAULT_DISCOVERY_LIMIT,
    DEFAULT_RECORDINGS_LIMIT,
} from "./constants.js";
import type {
    ActiveCall,
    AudioProfile,
    CallHistoryEntry,
    CallMode,
    Ringtone,
    RingtoneStatus,
    TelephoneConfig,
    TelephoneContact,
    Voicemail,
    VoicemailStatus,
} from "./types.js";

export type CallPageDataState = {
    config: TelephoneConfig | null;
    activeCall: ActiveCall | null;
    lastCall: ActiveCall | null;
    isCallEnded: boolean;
    wasDeclined: boolean;
    wasVoicemail: boolean;
    initiationStatus: string | null;
    initiationTargetHash: string | null;
    initiationTargetName: string | null;
    callHistory: CallHistoryEntry[];
    callHistorySearch: string;
    callHistoryLimit: number;
    callHistoryOffset: number;
    hasMoreCallHistory: boolean;
    voicemails: Voicemail[];
    unreadVoicemailsCount: number;
    voicemailStatus: Partial<VoicemailStatus>;
    contacts: TelephoneContact[];
    contactsSearch: string;
    discoveryAnnounces: unknown[];
    discoverySearch: string;
    discoveryLimit: number;
    discoveryOffset: number;
    hasMoreDiscovery: boolean;
    recordings: unknown[];
    recordingSearch: string;
    ringtones: Ringtone[];
    ringtoneStatus: Partial<RingtoneStatus>;
    audioProfiles: AudioProfile[];
    callModes: CallMode[];
    selectedAudioProfileId: number | string | null;
    selectedCallModeId: number | string | null;
    localMicMuted: boolean;
    localSpeakerMuted: boolean;
    localPttActive: boolean;
    isMicMuting: boolean;
    pttKeyHeld: boolean;
    webAudioBridgeRequired: boolean;
    endedTimeout: ReturnType<typeof setTimeout> | null;
};

/**
 * Creates the default data bag for CallPage
 */
export function createCallPageDataState(): CallPageDataState {
    return {
        config: null,
        activeCall: null,
        lastCall: null,
        isCallEnded: false,
        wasDeclined: false,
        wasVoicemail: false,
        initiationStatus: null,
        initiationTargetHash: null,
        initiationTargetName: null,
        callHistory: [],
        callHistorySearch: "",
        callHistoryLimit: DEFAULT_CALL_HISTORY_LIMIT,
        callHistoryOffset: 0,
        hasMoreCallHistory: false,
        voicemails: [],
        unreadVoicemailsCount: 0,
        voicemailStatus: {},
        contacts: [],
        contactsSearch: "",
        discoveryAnnounces: [],
        discoverySearch: "",
        discoveryLimit: DEFAULT_DISCOVERY_LIMIT,
        discoveryOffset: 0,
        hasMoreDiscovery: true,
        recordings: [],
        recordingSearch: "",
        ringtones: [],
        ringtoneStatus: {},
        audioProfiles: [],
        callModes: [],
        selectedAudioProfileId: null,
        selectedCallModeId: 1,
        localMicMuted: false,
        localSpeakerMuted: false,
        localPttActive: false,
        isMicMuting: false,
        pttKeyHeld: false,
        webAudioBridgeRequired: false,
        endedTimeout: null,
    };
}

/**
 * Loads telephone config into state
 */
export async function loadConfig(state: CallPageDataState): Promise<void> {
    try {
        const response = await fetchConfig();
        state.config = response.config || null;
    } catch (e) {
        console.log(e);
    }
}

/**
 * Loads audio profiles and default selection
 */
export async function loadAudioProfiles(state: CallPageDataState): Promise<void> {
    try {
        const response = await fetchAudioProfiles();
        state.audioProfiles = Array.isArray(response.audio_profiles) ? response.audio_profiles : [];
        if (response.default_audio_profile_id != null) {
            state.selectedAudioProfileId = response.default_audio_profile_id;
        }
    } catch (e) {
        console.log(e);
    }
}

/**
 * Loads call modes and default selection
 */
export async function loadCallModes(state: CallPageDataState): Promise<void> {
    try {
        const response = await fetchCallModes();
        state.callModes = Array.isArray(response.call_modes) ? response.call_modes : [];
        if (response.default_call_mode_id != null) {
            state.selectedCallModeId = response.default_call_mode_id;
        }
    } catch (e) {
        console.log(e);
    }
}

/**
 * Loads call history page
 */
export async function loadHistory(state: CallPageDataState, loadMore = false): Promise<void> {
    try {
        if (!loadMore) {
            state.callHistoryOffset = 0;
        }
        const response = await fetchCallHistory({
            limit: state.callHistoryLimit,
            offset: state.callHistoryOffset,
            search: state.callHistorySearch || undefined,
        });
        const newItems = response.call_history || [];
        state.callHistory = loadMore ? [...state.callHistory, ...newItems] : newItems;
        state.hasMoreCallHistory = newItems.length === state.callHistoryLimit;
        applyHydratedVisuals(state);
    } catch (e) {
        console.log(e);
    }
}

/**
 * Loads contacts list
 */
export async function loadContacts(state: CallPageDataState): Promise<void> {
    try {
        const response = await fetchContacts({ search: state.contactsSearch || undefined });
        if (Array.isArray(response)) {
            state.contacts = response;
        } else {
            state.contacts = response.contacts || [];
        }
        applyHydratedVisuals(state);
    } catch (e) {
        console.log(e);
    }
}

/**
 * Loads discovery announces for phonebook
 */
export async function loadDiscovery(state: CallPageDataState, loadMore = false): Promise<void> {
    try {
        if (!loadMore) {
            state.discoveryOffset = 0;
        }
        const response = await fetchDiscoveryAnnounces({
            limit: state.discoveryLimit,
            offset: state.discoveryOffset,
            search: state.discoverySearch || undefined,
        });
        const items = response.announces || [];
        state.discoveryAnnounces = loadMore ? [...state.discoveryAnnounces, ...items] : items;
        state.hasMoreDiscovery = items.length === state.discoveryLimit;
    } catch (e) {
        console.log(e);
    }
}

/**
 * Applies contact custom images onto call and history rows
 */
function applyHydratedVisuals(state: CallPageDataState): void {
    const hydrated = hydrateContactVisuals({
        contacts: state.contacts,
        activeCall: state.activeCall,
        lastCall: state.lastCall,
        callHistory: state.callHistory,
    });
    if (hydrated.activeCall !== undefined) {
        state.activeCall = hydrated.activeCall;
    }
    if (hydrated.lastCall !== undefined) {
        state.lastCall = hydrated.lastCall;
    }
    state.callHistory = hydrated.callHistory;
}

/**
 * Loads voicemails and unread count
 */
export async function loadVoicemails(state: CallPageDataState): Promise<void> {
    try {
        const response = await fetchVoicemails();
        state.voicemails = response.voicemails || [];
        state.unreadVoicemailsCount = response.unread_count ?? 0;
    } catch (e) {
        console.log(e);
    }
}

/**
 * Loads voicemail subsystem status
 */
export async function loadVoicemailStatus(state: CallPageDataState): Promise<void> {
    try {
        state.voicemailStatus = await fetchVoicemailStatus();
    } catch (e) {
        console.log(e);
    }
}

/**
 * Loads ringtones list
 */
export async function loadRingtones(state: CallPageDataState): Promise<void> {
    try {
        const response = await fetchRingtones();
        state.ringtones = Array.isArray(response) ? response : [];
    } catch (e) {
        console.log(e);
    }
}

/**
 * Loads ringtone status payload
 */
export async function loadRingtoneStatus(state: CallPageDataState): Promise<void> {
    try {
        state.ringtoneStatus = await fetchRingtoneStatus();
    } catch (e) {
        console.log(e);
    }
}

/**
 * Loads call recordings
 */
export async function loadRecordings(state: CallPageDataState): Promise<void> {
    try {
        const response = await fetchRecordings({
            limit: DEFAULT_RECORDINGS_LIMIT,
            search: state.recordingSearch || undefined,
        });
        state.recordings = response.recordings || [];
    } catch (e) {
        console.error("Failed to get recordings:", e);
    }
}

/**
 * Marks missed calls as viewed
 */
export async function markMissedCallsViewed(): Promise<void> {
    try {
        await apiMarkMissedCallsViewed();
    } catch (e) {
        console.log(e);
    }
}

/**
 * Clears call history then reloads
 */
export async function clearHistory(state: CallPageDataState): Promise<void> {
    try {
        await apiClearCallHistory();
        await loadHistory(state);
    } catch (e) {
        console.log(e);
    }
}

export type StatusApplyOptions = {
    ensureWebAudio?: (webAudio: { enabled?: boolean; required?: boolean; frame_ms?: number }) => Promise<void>;
    onCallEnded?: (oldCall: ActiveCall) => void;
    isPopout?: boolean;
};

/**
 * Applies telephone status response into page state
 */
export async function applyTelephoneStatus(
    state: CallPageDataState,
    options: StatusApplyOptions = {}
): Promise<void> {
    try {
        const response = await fetchTelephoneStatus();
        const oldCall = state.activeCall;
        const newCall = response.active_call ?? null;

        if (newCall) {
            if (!oldCall || newCall.hash !== oldCall.hash) {
                state.localMicMuted = Boolean(newCall.is_mic_muted);
                state.localSpeakerMuted = Boolean(newCall.is_speaker_muted);
                state.localPttActive = Boolean(newCall.is_ptt_active);
            } else if (!state.isMicMuting) {
                state.localMicMuted = Boolean(newCall.is_mic_muted ?? response.is_mic_muted ?? state.localMicMuted);
                state.localSpeakerMuted = Boolean(
                    newCall.is_speaker_muted ?? response.is_speaker_muted ?? state.localSpeakerMuted
                );
                if (!state.pttKeyHeld) {
                    state.localPttActive = Boolean(newCall.is_ptt_active);
                }
            }
            if (newCall.call_mode_id != null) {
                state.selectedCallModeId = newCall.call_mode_id;
            }
        } else {
            state.localPttActive = false;
            state.pttKeyHeld = false;
        }

        state.activeCall = newCall;
        state.initiationStatus = response.initiation_status ?? null;
        state.initiationTargetHash = response.initiation_target_hash ?? null;
        state.initiationTargetName = response.initiation_target_name ?? null;

        if (state.activeCall?.is_voicemail) {
            state.wasVoicemail = true;
        }
        if (response.voicemail) {
            state.unreadVoicemailsCount = response.voicemail.unread_count ?? state.unreadVoicemailsCount;
        }
        if (response.web_audio && options.ensureWebAudio) {
            await options.ensureWebAudio(response.web_audio);
        }

        applyHydratedVisuals(state);

        if (oldCall != null && state.activeCall == null) {
            void loadHistory(state);
            void loadVoicemails(state);
            state.lastCall = oldCall;
            state.isCallEnded = true;
            options.onCallEnded?.(oldCall);
            if (state.endedTimeout) clearTimeout(state.endedTimeout);
            state.endedTimeout = setTimeout(() => {
                state.isCallEnded = false;
                state.lastCall = null;
                if (options.isPopout && typeof window !== "undefined") {
                    window.close();
                }
            }, CALL_ENDED_RESET_TIMEOUT_MS);
        } else if (state.activeCall != null) {
            state.isCallEnded = false;
            state.wasDeclined = false;
            state.wasVoicemail = false;
            state.lastCall = null;
            if (state.endedTimeout) clearTimeout(state.endedTimeout);
        } else if (!state.endedTimeout) {
            state.isCallEnded = false;
            state.wasDeclined = false;
            state.wasVoicemail = false;
            state.lastCall = null;
        }
    } catch (e) {
        console.log(e);
    }
}
