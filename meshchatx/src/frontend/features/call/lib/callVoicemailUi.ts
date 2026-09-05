// SPDX-License-Identifier: 0BSD

import DialogUtils from "../../../js/DialogUtils.js";
import { t } from "../../../js/i18n.js";
import ToastUtils from "../../../js/ToastUtils.js";
import {
    deleteRecording,
    deleteVoicemail,
    deleteVoicemailGreeting,
    generateVoicemailGreeting,
    markVoicemailAsRead,
    patchConfig,
    startRecordingGreetingMic,
    stopRecordingGreetingMic,
    uploadVoicemailGreeting,
} from "./callApi.js";
import type { TelephoneConfig, Voicemail } from "./types.js";

export interface VoicemailItem {
    id: number | string;
    remote_identity_name?: string;
    remote_identity_hash?: string;
    remote_destination_hash?: string;
    remote_telephony_hash?: string;
    timestamp?: number;
    duration?: number;
    duration_seconds?: number;
    is_read?: boolean;
    remote_icon?: {
        icon_name?: string;
        foreground_colour?: string;
        background_colour?: string;
    };
    [key: string]: unknown;
}

export interface VoicemailConfig {
    voicemail_enabled?: boolean;
    voicemail_greeting?: string;
    voicemail_tts_speed?: number;
    voicemail_tts_pitch?: number;
    voicemail_tts_word_gap?: number;
    voicemail_tts_voice?: string;
    voicemail_auto_answer_delay_seconds?: number;
    voicemail_max_recording_seconds?: number;
    [key: string]: unknown;
}

export interface VoicemailStatusState {
    has_espeak?: boolean;
    has_greeting?: boolean;
    is_greeting_recording?: boolean;
    [key: string]: unknown;
}

export interface ContactLookupResult {
    custom_image?: string;
    name?: string;
    [key: string]: unknown;
}

export interface CallVoicemailTabProps {
    active?: boolean;
    voicemailSearch?: string;
    config?: VoicemailConfig | null;
    voicemailStatus?: VoicemailStatusState;
    voicemails?: VoicemailItem[];
    isGeneratingGreeting?: boolean;
    isUploadingGreeting?: boolean;
    isPlayingGreeting?: boolean;
    getContactByHash?: (hash: string) => ContactLookupResult | undefined;
    formatDateTime?: (timestamp: number) => string;
    formatDuration?: (seconds?: number) => string;
    formatDestinationHash?: (hash?: string) => string;
    onsearchinput?: (value: string) => void;
    onupdateconfig?: (patch: Partial<VoicemailConfig>) => void;
    onpatchconfig?: (patch: Partial<VoicemailConfig>) => void;
    onsaveandgenerate?: () => void;
    onuploadgreeting?: (event: Event) => void;
    onstartrecordinggreeting?: () => void;
    onstoprecordinggreeting?: () => void;
    ondeletegreeting?: () => void;
    onplaygreeting?: () => void;
    oncopyhash?: (hash: string) => void;
    onmarkread?: (voicemail: VoicemailItem) => void;
    oncallback?: (destination: string) => void;
    ondelete?: (id: number | string) => void;
}

/**
 * Resolves the destination hash to use when calling back from a voicemail
 */
export function resolveCallbackHash(voicemail: VoicemailItem): string {
    return voicemail.remote_telephony_hash || voicemail.remote_destination_hash || voicemail.remote_identity_hash || "";
}

/**
 * Generates the API endpoint URL for streaming voicemail audio
 */
export function getVoicemailAudioSrc(voicemailId: number | string): string {
    return `/api/v1/telephone/voicemails/${encodeURIComponent(String(voicemailId))}/audio`;
}

/**
 * Generates the download file name for a voicemail audio file
 */
export function getVoicemailDownloadFileName(voicemailId: number | string): string {
    return `voicemail_${voicemailId}.opus`;
}

/**
 * Saves voicemail greeting configuration and generates speech audio
 */
export async function executeSaveAndGenerateGreeting(
    config: Partial<TelephoneConfig>
): Promise<TelephoneConfig | null> {
    try {
        const patchRes = await patchConfig({
            voicemail_greeting: config.voicemail_greeting,
            voicemail_tts_speed: config.voicemail_tts_speed,
            voicemail_tts_pitch: config.voicemail_tts_pitch,
            voicemail_tts_word_gap: config.voicemail_tts_word_gap,
            voicemail_tts_voice: config.voicemail_tts_voice,
        });
        await generateVoicemailGreeting();
        ToastUtils.success(t("call.greeting_generated"));
        return patchRes.config;
    } catch {
        ToastUtils.error(t("call.failed_to_generate_greeting"));
        return null;
    }
}

/**
 * Uploads a custom greeting audio file
 */
export async function executeUploadGreeting(file: File): Promise<boolean> {
    try {
        const formData = new FormData();
        formData.append("file", file);
        await uploadVoicemailGreeting(formData);
        ToastUtils.success(t("call.greeting_uploaded"));
        return true;
    } catch {
        ToastUtils.error(t("call.failed_to_upload_greeting"));
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
export async function executeMarkVoicemailRead(
    voicemail: Partial<Voicemail> & { id: number | string }
): Promise<boolean> {
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
