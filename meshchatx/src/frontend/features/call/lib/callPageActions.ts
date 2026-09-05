// SPDX-License-Identifier: 0BSD

import { t } from "../../../js/i18n.js";
import ToastUtils from "../../../js/ToastUtils.js";
import {
    answerCall,
    blockDestination,
    clearCallHistory,
    hangupCall,
    initiateCall,
    markMissedCallsViewed,
    muteReceive,
    muteTransmit,
    patchConfig,
    sendToVoicemail,
    setPttActive as apiSetPttActive,
    switchAudioProfile as apiSwitchAudioProfile,
    switchCallMode as apiSwitchCallMode,
    unmuteReceive,
    unmuteTransmit,
} from "./callApi.js";
import { resolveContactByHash, sanitizeCallInputHash } from "./callHistory.js";
import type { ActiveCall, TelephoneConfig, TelephoneContact } from "./types.js";

export { executeCompressContactImage, executeDeleteContact, executeSaveContact } from "./callApiContacts.js";

export {
    executeDeleteRingtone,
    executeSaveRingtoneName,
    executeSetPrimaryRingtone,
    executeUploadRingtone,
} from "./callApiRingtones.js";

export {
    executeDeleteGreeting,
    executeDeleteRecording,
    executeDeleteVoicemail,
    executeGenerateGreeting,
    executeMarkVoicemailRead,
    executeSaveAndGenerateGreeting,
    executeStartRecordingGreetingMic,
    executeStopRecordingGreetingMic,
    executeUploadGreeting,
} from "./callVoicemailUi.js";

export const executeVoicemailSaveAndGenerate = async (config: Partial<TelephoneConfig>) => {
    const { executeSaveAndGenerateGreeting } = await import("./callVoicemailUi.js");
    return executeSaveAndGenerateGreeting(config);
};

export interface MutableCallState {
    config?: Partial<TelephoneConfig> | null;
    activeCall?: Partial<ActiveCall> | null;
    lastCall?: Partial<ActiveCall> | null;
    isCallEnded?: boolean;
    wasDeclined?: boolean;
    wasVoicemail?: boolean;
    initiationStatus?: string | null;
    initiationTargetHash?: string | null;
    initiationTargetName?: string | null;
    localMicMuted?: boolean;
    localSpeakerMuted?: boolean;
    localPttActive?: boolean;
    isMicMuting?: boolean;
    isSpeakerMuting?: boolean;
    selectedAudioProfileId?: number | string | null;
    selectedCallModeId?: number | string | null;
    contacts?: TelephoneContact[];
    [key: string]: unknown;
}

/**
 * Initiates an outgoing call to the specified identity or contact
 */
export async function executeCall(params: {
    destinationInput: string;
    contacts: TelephoneContact[];
    webAudioBridgeEnabled: boolean;
    onRequestMic: () => Promise<boolean>;
}): Promise<{ success: boolean; cleanedHash: string; targetName: string | null }> {
    const { destinationInput, contacts, webAudioBridgeEnabled, onRequestMic } = params;
    if (!destinationInput || !destinationInput.trim()) {
        ToastUtils.error(t("call.enter_identity_hash_to_call_error"));
        return { success: false, cleanedHash: "", targetName: null };
    }
    const cleanedHash = sanitizeCallInputHash(destinationInput, contacts);
    const matchedContact = resolveContactByHash(cleanedHash, contacts);
    const targetName = matchedContact ? matchedContact.name : null;
    try {
        if (webAudioBridgeEnabled) await onRequestMic();
        await initiateCall(cleanedHash);
        return { success: true, cleanedHash, targetName };
    } catch (e: any) {
        ToastUtils.error(e?.response?.data?.message || t("call.failed_to_initiate_call"));
        return { success: false, cleanedHash, targetName };
    }
}

/**
 * Answers an incoming call
 */
export async function executeAnswer(params?: {
    webAudioBridgeEnabled?: boolean;
    onRequestMic?: () => Promise<boolean>;
}): Promise<boolean> {
    try {
        if (params?.webAudioBridgeEnabled && params.onRequestMic) await params.onRequestMic();
        await answerCall();
        return true;
    } catch {
        ToastUtils.error(t("call.failed_to_answer_call"));
        return false;
    }
}

/**
 * Hangs up or rejects an active call
 */
export async function executeHangup(activeCall?: ActiveCall | null): Promise<{
    success: boolean;
    wasDeclined: boolean;
}> {
    const wasDeclined = Boolean(activeCall && activeCall.is_incoming && activeCall.status === 4);
    try {
        await hangupCall();
        return { success: true, wasDeclined };
    } catch {
        ToastUtils.error(t("call.failed_to_hangup_call"));
        return { success: false, wasDeclined };
    }
}

/**
 * Sends incoming ringing call to voicemail
 */
export async function executeSendToVoicemail(): Promise<boolean> {
    try {
        await sendToVoicemail();
        return true;
    } catch {
        ToastUtils.error(t("call.failed_to_send_to_voicemail"));
        return false;
    }
}

/**
 * Toggles microphone mute state
 */
export async function executeToggleMicrophone(isMuted: boolean): Promise<boolean> {
    try {
        if (isMuted) {
            await unmuteTransmit();
            return false;
        }
        await muteTransmit();
        return true;
    } catch {
        ToastUtils.error(t(isMuted ? "call.failed_to_unmute_mic" : "call.failed_to_mute_mic"));
        return isMuted;
    }
}
export async function executeToggleMic(isMuted: boolean): Promise<boolean> {
    return executeToggleMicrophone(isMuted);
}

/**
 * Toggles speaker mute state
 */
export async function executeToggleSpeaker(isMuted: boolean): Promise<boolean> {
    try {
        if (isMuted) {
            await unmuteReceive();
            return false;
        }
        await muteReceive();
        return true;
    } catch {
        ToastUtils.error(t(isMuted ? "call.failed_to_unmute_speaker" : "call.failed_to_mute_speaker"));
        return isMuted;
    }
}

/**
 * Switches the active call mode
 */
export async function executeSwitchCallMode(modeId: number | string): Promise<{
    modeId: number | string;
    isPttActive: boolean;
    isHalfDuplex: boolean;
}> {
    const numericModeId = Number(modeId);
    try {
        await apiSwitchCallMode(numericModeId);
        const isHalfDuplex = numericModeId === 1;
        return {
            modeId: numericModeId,
            isPttActive: false,
            isHalfDuplex,
        };
    } catch {
        ToastUtils.error(t("call.failed_to_switch_call_mode"));
        return {
            modeId,
            isPttActive: false,
            isHalfDuplex: false,
        };
    }
}

/**
 * Switches the active audio profile
 */
export async function executeSwitchAudioProfile(profileId: number | string): Promise<number | string | null> {
    try {
        await apiSwitchAudioProfile(profileId);
        return profileId;
    } catch {
        ToastUtils.error(t("call.failed_to_switch_audio_profile"));
        return null;
    }
}

/**
 * Sets half duplex push-to-talk transmission state
 */
export async function executeSetPttActive(active: boolean, isHalfDuplex?: boolean): Promise<boolean> {
    if (isHalfDuplex !== undefined && !isHalfDuplex && active) {
        return false;
    }
    try {
        await apiSetPttActive(active);
        return active;
    } catch {
        return false;
    }
}
export async function executeSetPtt(active: boolean, isHalfDuplex?: boolean): Promise<boolean> {
    return executeSetPttActive(active, isHalfDuplex);
}

/**
 * Clears call history
 */
export async function executeClearCallHistory(): Promise<boolean> {
    try {
        await clearCallHistory();
        return true;
    } catch {
        return false;
    }
}

/**
 * Blocks a destination from calling
 */
export async function executeBlockIdentity(destinationHash: string): Promise<boolean> {
    try {
        await blockDestination(destinationHash);
        ToastUtils.success(t("common.blocked"));
        return true;
    } catch {
        ToastUtils.error(t("common.error"));
        return false;
    }
}

/**
 * Copies a hash string to clipboard
 */
export async function executeCopyHash(hash?: string | null): Promise<boolean> {
    if (!hash) return false;
    try {
        if (typeof navigator !== "undefined" && navigator.clipboard) {
            await navigator.clipboard.writeText(hash);
            ToastUtils.success(t("call.hash_copied"));
            return true;
        }
        return false;
    } catch (e) {
        console.error(e);
        ToastUtils.error(t("call.failed_to_copy_hash"));
        return false;
    }
}

/**
 * Updates application configuration patch
 */
export async function executePatchConfig(patch: Partial<TelephoneConfig>): Promise<TelephoneConfig | null> {
    try {
        const res = await patchConfig(patch);
        return res.config;
    } catch {
        return null;
    }
}

/**
 * Marks all missed calls as viewed
 */
export async function executeMarkMissedCallsViewed(): Promise<void> {
    try {
        await markMissedCallsViewed();
    } catch {
        // ignore failure
    }
}

export async function executeToggleWebAudio(
    config: Partial<TelephoneConfig> | null,
    newVal: boolean,
    webAudioBridgeRequired: boolean
): Promise<boolean> {
    if (!config || (webAudioBridgeRequired && !newVal)) return Boolean(config?.telephone_web_audio_enabled);
    const updated = await executePatchConfig({ telephone_web_audio_enabled: newVal });
    return Boolean(updated?.telephone_web_audio_enabled);
}

export async function placeOutgoingCall(params: {
    destinationInput: string;
    contacts: TelephoneContact[];
    webAudioBridgeEnabled: boolean;
    onRequestMic: () => Promise<boolean>;
}): Promise<{ success: boolean; cleanedHash: string; targetName: string | null }> {
    return executeCall(params);
}

export async function answerIncomingCall(params?: {
    webAudioBridgeEnabled?: boolean;
    onRequestMic?: () => Promise<boolean>;
}): Promise<boolean> {
    return executeAnswer(params);
}

export async function hangupActiveCall(activeCall?: ActiveCall | null): Promise<{
    success: boolean;
    wasDeclined: boolean;
}> {
    return executeHangup(activeCall);
}

export async function sendActiveCallToVoicemail(): Promise<boolean> {
    return executeSendToVoicemail();
}

export async function toggleMicrophone(isMuted: boolean): Promise<boolean> {
    return executeToggleMicrophone(isMuted);
}

export async function toggleSpeaker(isMuted: boolean): Promise<boolean> {
    return executeToggleSpeaker(isMuted);
}

export async function updateTelephoneConfig(patch: Partial<TelephoneConfig>): Promise<TelephoneConfig | null> {
    return executePatchConfig(patch);
}

export async function switchCallMode(modeId: number | string): Promise<{
    modeId: number | string;
    isPttActive: boolean;
    isHalfDuplex: boolean;
}> {
    return executeSwitchCallMode(modeId);
}

export async function switchAudioProfile(profileId: number | string): Promise<number | string | null> {
    return executeSwitchAudioProfile(profileId);
}
