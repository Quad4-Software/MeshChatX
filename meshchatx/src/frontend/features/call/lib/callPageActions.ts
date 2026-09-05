// SPDX-License-Identifier: 0BSD

import Compressor from "compressorjs";
import DialogUtils from "../../../js/DialogUtils.js";
import { t } from "../../../js/i18n.js";
import ToastUtils from "../../../js/ToastUtils.js";
import {
    answerCall,
    blockDestination,
    clearCallHistory,
    createContact,
    deleteContact,
    deleteRecording,
    deleteRingtone,
    deleteVoicemail,
    deleteVoicemailGreeting,
    generateVoicemailGreeting,
    hangupCall,
    initiateCall,
    markMissedCallsViewed,
    markVoicemailAsRead,
    muteReceive,
    muteTransmit,
    patchConfig,
    patchRingtone,
    sendToVoicemail,
    setPttActive,
    startRecordingGreetingMic,
    stopRecordingGreetingMic,
    switchAudioProfile,
    switchCallMode,
    unmuteReceive,
    unmuteTransmit,
    updateContact,
    uploadRingtone,
    uploadVoicemailGreeting,
} from "./callApi.js";
import { resolveContactByHash, sanitizeCallInputHash } from "./callHistory.js";
import type { ActiveCall, TelephoneConfig, TelephoneContact, Voicemail } from "./types.js";

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
export async function executeAnswer(params: {
    webAudioBridgeEnabled: boolean;
    onRequestMic: () => Promise<boolean>;
}): Promise<boolean> {
    try {
        if (params.webAudioBridgeEnabled) await params.onRequestMic();
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
export async function executeHangup(activeCall: ActiveCall | null | undefined): Promise<{
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
 * Sends an incoming call to voicemail
 */
export async function executeSendToVoicemail(): Promise<boolean> {
    try {
        await sendToVoicemail();
        ToastUtils.success(t("call.call_sent_to_voicemail"));
        return true;
    } catch {
        ToastUtils.error(t("call.failed_to_send_to_voicemail"));
        return false;
    }
}

/**
 * Toggles microphone mute state
 */
export async function executeToggleMicrophone(isCurrentlyMuted: boolean): Promise<boolean> {
    try {
        if (isCurrentlyMuted) await unmuteTransmit();
        else await muteTransmit();
        return !isCurrentlyMuted;
    } catch {
        ToastUtils.error(t("call.failed_to_toggle_microphone"));
        return isCurrentlyMuted;
    }
}

/**
 * Toggles speaker mute state
 */
export async function executeToggleSpeaker(isCurrentlyMuted: boolean): Promise<boolean> {
    try {
        if (isCurrentlyMuted) await unmuteReceive();
        else await muteReceive();
        return !isCurrentlyMuted;
    } catch {
        ToastUtils.error(t("call.failed_to_toggle_speaker"));
        return isCurrentlyMuted;
    }
}

/**
 * Switches the active call mode
 */
export async function executeSwitchCallMode(modeId: number | string): Promise<{
    modeId?: number;
    isHalfDuplex?: boolean;
    isPttActive?: boolean;
}> {
    try {
        const res = await switchCallMode(modeId);
        return { modeId: res.mode_id, isHalfDuplex: res.is_half_duplex, isPttActive: res.is_ptt_active };
    } catch {
        ToastUtils.error(t("call.failed_to_switch_call_mode"));
        return {};
    }
}

/**
 * Switches the active audio profile
 */
export async function executeSwitchAudioProfile(profileId: number | string): Promise<number | null> {
    try {
        const res = await switchAudioProfile(profileId);
        if (res.remapped) ToastUtils.warning(t("call.codec2_profile_remapped"));
        return res.profile_id != null ? res.profile_id : Number(profileId);
    } catch {
        ToastUtils.error(t("call.failed_to_switch_audio_profile"));
        return null;
    }
}

/**
 * Updates push to talk transmission state
 */
export async function executeSetPttActive(wantActive: boolean, isHalfDuplex: boolean): Promise<boolean> {
    if (!isHalfDuplex && wantActive) return false;
    try {
        await setPttActive(wantActive);
        return wantActive;
    } catch {
        if (wantActive) ToastUtils.error(t("call.failed_to_set_ptt"));
        return !wantActive;
    }
}

/**
 * Saves a new or edited contact
 */
export async function executeSaveContact(
    contact: Partial<TelephoneContact>,
    editingContact?: TelephoneContact | null
): Promise<boolean> {
    if (!contact.name || !contact.remote_identity_hash) {
        ToastUtils.error(t("call.name_and_hash_required"));
        return false;
    }
    try {
        if (contact.id) {
            if (editingContact && editingContact.custom_image && !contact.custom_image) {
                contact.clear_image = true;
            }
            await updateContact(contact.id, contact);
            ToastUtils.success(t("call.contact_updated"));
        } else {
            await createContact(contact);
            ToastUtils.success(t("call.contact_added"));
        }
        return true;
    } catch (e: any) {
        ToastUtils.error(e?.response?.data?.message || t("call.failed_to_save_contact"));
        return false;
    }
}

/**
 * Deletes a contact with confirmation dialog
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

/**
 * Compresses an image file for contact avatar
 */
export function executeCompressContactImage(file: File, onSuccess: (dataUrl: string) => void): void {
    new Compressor(file, {
        maxWidth: 256,
        maxHeight: 256,
        quality: 0.7,
        mimeType: "image/webp",
        success: (result: Blob | File) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                if (typeof e.target?.result === "string") onSuccess(e.target.result);
            };
            reader.readAsDataURL(result);
        },
        error: (err: Error) => {
            ToastUtils.error(err.message);
        },
    });
}

/**
 * Saves updated ringtone display name
 */
export async function executeSaveRingtoneName(ringtoneId: number | string, displayName: string): Promise<boolean> {
    try {
        await patchRingtone(ringtoneId, { display_name: displayName });
        return true;
    } catch (e) {
        console.error(e);
        ToastUtils.error(t("call.failed_to_update_ringtone_name"));
        return false;
    }
}

/**
 * Sets a ringtone as primary
 */
export async function executeSetPrimaryRingtone(ringtoneId: number | string): Promise<boolean> {
    try {
        await patchRingtone(ringtoneId, { is_primary: true });
        ToastUtils.success(t("call.primary_ringtone_set"));
        return true;
    } catch (e) {
        console.error(e);
        ToastUtils.error(t("call.failed_to_set_primary_ringtone"));
        return false;
    }
}

/**
 * Deletes a ringtone with confirmation
 */
export async function executeDeleteRingtone(ringtoneId: number | string): Promise<boolean> {
    const confirmed = await DialogUtils.confirm(t("call.delete_ringtone_confirm"));
    if (!confirmed) return false;
    try {
        await deleteRingtone(ringtoneId);
        ToastUtils.success(t("call.ringtone_deleted"));
        return true;
    } catch {
        ToastUtils.error(t("call.failed_to_delete_ringtone"));
        return false;
    }
}

/**
 * Uploads a ringtone audio file
 */
export async function executeUploadRingtone(file: File): Promise<boolean> {
    const formData = new FormData();
    formData.append("file", file);
    try {
        await uploadRingtone(formData);
        ToastUtils.success(t("call.ringtone_uploaded_successfully"));
        return true;
    } catch (e: any) {
        console.error(e);
        ToastUtils.error(e?.response?.data?.message || t("call.failed_to_upload_ringtone"));
        return false;
    }
}

/**
 * Generates voicemail greeting via text to speech
 */
export async function executeGenerateGreeting(): Promise<boolean> {
    try {
        await generateVoicemailGreeting();
        ToastUtils.success(t("call.greeting_generated_successfully"));
        return true;
    } catch (e: any) {
        ToastUtils.error(e?.response?.data?.message || t("call.failed_to_generate_greeting"));
        return false;
    }
}

/**
 * Uploads a custom voicemail greeting audio file
 */
export async function executeUploadGreeting(file: File): Promise<boolean> {
    const formData = new FormData();
    formData.append("file", file);
    try {
        await uploadVoicemailGreeting(formData);
        ToastUtils.success(t("call.greeting_uploaded_successfully"));
        return true;
    } catch (e: any) {
        ToastUtils.error(e?.response?.data?.message || t("call.failed_to_upload_greeting"));
        return false;
    }
}

/**
 * Deletes custom voicemail greeting
 */
export async function executeDeleteGreeting(): Promise<boolean> {
    const confirmed = await DialogUtils.confirm(t("call.delete_greeting_confirm"));
    if (!confirmed) return false;
    try {
        await deleteVoicemailGreeting();
        ToastUtils.success(t("call.greeting_deleted"));
        return true;
    } catch {
        ToastUtils.error(t("call.failed_to_delete_greeting"));
        return false;
    }
}

/**
 * Starts recording voicemail greeting from microphone
 */
export async function executeStartRecordingGreetingMic(): Promise<boolean> {
    try {
        await startRecordingGreetingMic();
        return true;
    } catch {
        ToastUtils.error(t("call.failed_to_start_recording_greeting"));
        return false;
    }
}

/**
 * Stops recording voicemail greeting from microphone
 */
export async function executeStopRecordingGreetingMic(): Promise<boolean> {
    try {
        await stopRecordingGreetingMic();
        ToastUtils.success(t("call.greeting_recorded_from_mic"));
        return true;
    } catch {
        ToastUtils.error(t("call.failed_to_stop_recording_greeting"));
        return false;
    }
}

/**
 * Deletes a voicemail entry
 */
export async function executeDeleteVoicemail(voicemailId: number | string): Promise<boolean> {
    try {
        await deleteVoicemail(voicemailId);
        ToastUtils.success(t("call.voicemail_deleted"));
        return true;
    } catch {
        ToastUtils.error(t("call.failed_to_delete_voicemail"));
        return false;
    }
}

/**
 * Marks a voicemail entry as read
 */
export async function executeMarkVoicemailRead(voicemail: Partial<Voicemail> & { id: number | string }): Promise<boolean> {
    if (voicemail.is_read) return true;
    try {
        await markVoicemailAsRead(voicemail.id);
        voicemail.is_read = 1;
        return true;
    } catch (e) {
        console.error(e);
        return false;
    }
}

/**
 * Deletes a call recording entry
 */
export async function executeDeleteRecording(recordingId: number | string): Promise<boolean> {
    const confirmed = await DialogUtils.confirm(t("call.delete_recording_confirm"));
    if (!confirmed) return false;
    try {
        await deleteRecording(recordingId);
        ToastUtils.success(t("call.recording_deleted"));
        return true;
    } catch {
        ToastUtils.error(t("call.failed_to_delete_recording"));
        return false;
    }
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
export async function executeCopyHash(hash: string): Promise<boolean> {
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
