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
    startRecordingGreetingMic,
    stopRecordingGreetingMic,
    uploadVoicemailGreeting,
} from "./callApiVoicemail.js";
import type { TelephoneConfig, TelephoneContact, Voicemail, VoicemailStatus } from "./types.js";

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

export interface VoicemailTtsField {
    key: "voicemail_tts_speed" | "voicemail_tts_pitch" | "voicemail_tts_word_gap" | "voicemail_tts_voice";
    id: string;
    labelKey: string;
    type: "number" | "text";
    min?: number;
    max?: number;
    step?: number;
}

export const VOICEMAIL_TTS_FIELDS: VoicemailTtsField[] = [
    {
        key: "voicemail_tts_speed",
        id: "voicemail-tts-speed",
        labelKey: "call.tts_speed",
        type: "number",
        min: 80,
        max: 450,
    },
    {
        key: "voicemail_tts_pitch",
        id: "voicemail-tts-pitch",
        labelKey: "call.tts_pitch",
        type: "number",
        min: 0,
        max: 99,
    },
    {
        key: "voicemail_tts_word_gap",
        id: "voicemail-tts-gap",
        labelKey: "call.tts_word_gap",
        type: "number",
        min: 0,
        max: 100,
    },
    { key: "voicemail_tts_voice", id: "voicemail-tts-voice", labelKey: "call.tts_voice", type: "text" },
];

export interface VoicemailTimingField {
    key: "voicemail_auto_answer_delay_seconds" | "voicemail_max_recording_seconds";
    id: string;
    labelKey: string;
    min: number;
    max: number;
}

export const VOICEMAIL_TIMING_FIELDS: VoicemailTimingField[] = [
    {
        key: "voicemail_auto_answer_delay_seconds",
        id: "voicemail-answer-delay",
        labelKey: "call.answer_delay_seconds",
        min: 1,
        max: 120,
    },
    {
        key: "voicemail_max_recording_seconds",
        id: "voicemail-max-rec",
        labelKey: "call.max_recording_seconds",
        min: 5,
        max: 300,
    },
];

export const VOICEMAIL_STYLES = {
    switchBtn:
        "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus-ring-sem",
    switchThumb:
        "pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-xs ring-0 transition duration-200 ease-in-out",
    label: "text-xs font-bold text-sem-fg-muted uppercase tracking-wider block",
    labelMini: "text-[10px] font-bold text-sem-fg-muted uppercase tracking-wider block",
    textarea: "input-field w-full",
    inputSm: "input-field w-full text-xs py-1.5",
    inputLg: "input-field w-full text-sm py-2",
    greetingUploadBtn:
        "text-xs px-4 py-2 bg-sem-surface-muted text-sem-fg font-bold rounded-xl hover:bg-sem-surface-subtle transition-colors flex items-center gap-2 disabled:opacity-50 focus-ring-sem cursor-pointer",
    greetingDeleteBtn:
        "text-xs px-3 py-2 text-sem-danger hover:bg-sem-danger/10 rounded-xl font-bold transition-colors flex items-center gap-1 focus-ring-sem cursor-pointer",
    greetingPlayBtn:
        "text-xs px-3 py-2 bg-sem-accent-subtle text-sem-accent rounded-xl font-bold hover:bg-sem-accent-subtle/80 transition-colors flex items-center gap-1 focus-ring-sem cursor-pointer",
    actionBtn:
        "text-xs font-semibold text-sem-fg-muted hover:text-sem-accent flex items-center gap-1 transition-colors focus-ring-sem cursor-pointer",
    deleteBtn:
        "text-xs font-semibold text-sem-danger hover:text-sem-danger/80 flex items-center gap-1 transition-colors focus-ring-sem cursor-pointer",
};

export interface CallVoicemailSettingsProps {
    config?: VoicemailConfig | TelephoneConfig | Record<string, any> | null;
    voicemailStatus?: VoicemailStatusState | VoicemailStatus | Record<string, any> | null;
    isGeneratingGreeting?: boolean;
    isUploadingGreeting?: boolean;
    isPlayingGreeting?: boolean;
    onupdateconfig?: (cfg: Partial<VoicemailConfig> | Record<string, any>) => void;
    onpatchconfig?: (cfg: Partial<VoicemailConfig> | Record<string, any>) => void;
    onsaveandgenerate?: () => void;
    onuploadgreeting?: (e: Event, f: File) => void;
    onstartrecordinggreeting?: () => void;
    onstoprecordinggreeting?: () => void;
    ondeletegreeting?: () => void;
    onplaygreeting?: () => void;
}

export interface CallVoicemailTabProps {
    active?: boolean;
    isLoading?: boolean;
    config?: VoicemailConfig | TelephoneConfig | Record<string, any> | null;
    voicemails?: (VoicemailItem | Voicemail)[];
    voicemailStatus?: VoicemailStatusState | VoicemailStatus | Record<string, any> | null;
    voicemailSearch?: string;
    isGeneratingGreeting?: boolean;
    isUploadingGreeting?: boolean;
    isPlayingGreeting?: boolean;
    formatDateTime?: (ts: number) => string;
    formatDuration?: (s?: number) => string;
    formatDestinationHash?: (h?: string) => string;
    getContactByHash?: (h: string) => ContactLookupResult | TelephoneContact | null | undefined;
    onsearchinput?: (val: string) => void;
    onupdateconfig?: (cfg: Partial<VoicemailConfig> | Record<string, any>) => void;
    onpatchconfig?: (cfg: Partial<VoicemailConfig> | Record<string, any>) => void;
    onsaveandgenerate?: () => void;
    onuploadgreeting?: (e: Event, f: File) => void;
    onstartrecordinggreeting?: () => void;
    onstoprecordinggreeting?: () => void;
    ondeletegreeting?: () => void;
    onplaygreeting?: () => void;
    oncallback?: (h?: string) => void;
    oncopyhash?: (h?: string) => void;
    onmarkread?: (vm: any) => void;
    ondelete?: (id: number | string) => void;
}

/**
 * Resolves destination hash for calling back from a voicemail item
 */
export function resolveCallbackHash(voicemail: VoicemailItem): string | undefined {
    return voicemail.remote_identity_hash || voicemail.remote_destination_hash || voicemail.remote_telephony_hash;
}

/**
 * Generates API URL for voicemail audio playback
 */
export function getVoicemailAudioSrc(voicemailId: number | string): string {
    return `/api/v1/telephone/voicemails/${encodeURIComponent(String(voicemailId))}/audio`;
}

/**
 * Generates download file name for voicemail audio file
 */
export function getVoicemailDownloadFileName(voicemailId: number | string): string {
    return `voicemail_${voicemailId}.opus`;
}

/**
 * Formats voicemail timestamp using provided formatter or fallback
 */
export function formatVoicemailTimestamp(ts?: number | string, formatter?: (t: number) => string): string {
    const numeric = Number(ts || 0) * 1000;
    return formatter ? formatter(numeric) : String(numeric);
}

/**
 * Formats voicemail duration using provided formatter or fallback
 */
export function formatVoicemailDuration(item: VoicemailItem, formatter?: (s?: number) => string): string {
    const s = item.duration_seconds ?? item.duration ?? 0;
    return formatter ? formatter(s) : String(s);
}

/**
 * Formats voicemail destination hash using provided formatter or fallback
 */
export function formatVoicemailHash(hash?: string, formatter?: (h?: string) => string): string {
    return formatter ? formatter(hash) : hash || "";
}

/**
 * Returns background class for toggle switch
 */
export function getSwitchBgClass(enabled?: boolean): string {
    return enabled ? "bg-sem-accent" : "bg-sem-surface-muted";
}

/**
 * Returns translate class for toggle switch thumb
 */
export function getSwitchThumbClass(enabled?: boolean): string {
    return enabled ? "translate-x-5" : "translate-x-0";
}

/**
 * Returns class for greeting recording button
 */
export function getRecordBtnClass(isRecording?: boolean): string {
    return isRecording
        ? "bg-sem-danger text-white animate-pulse"
        : "bg-sem-surface-muted text-sem-fg-muted hover:bg-sem-surface-subtle";
}

/**
 * Returns class for voicemail list item
 */
export function getVoicemailItemClass(isRead?: boolean): string {
    return isRead ? "" : "bg-sem-accent-subtle/30";
}

/**
 * Resolves props for LxmfUserIcon in voicemail item
 */
export function resolveVoicemailUserIcon(
    voicemail: VoicemailItem,
    getContact?: (hash: string) => ContactLookupResult | undefined
) {
    return {
        customImage: getContact?.(voicemail.remote_identity_hash || "")?.custom_image || undefined,
        iconName: voicemail.remote_icon?.icon_name || "",
        iconForegroundColour: voicemail.remote_icon?.foreground_colour || "",
        iconBackgroundColour: voicemail.remote_icon?.background_colour || "",
    };
}

export async function executeSaveAndGenerateGreeting(
    config: Partial<TelephoneConfig>
): Promise<TelephoneConfig | null> {
    try {
        const res = await generateVoicemailGreeting({
            greeting: config.voicemail_greeting || "",
            tts_speed: config.voicemail_tts_speed ?? 175,
            tts_pitch: config.voicemail_tts_pitch ?? 50,
            tts_word_gap: config.voicemail_tts_word_gap ?? 10,
            tts_voice: config.voicemail_tts_voice || "en",
        });
        ToastUtils.success(t("call.greeting_generated_success"));
        return (res as unknown as { config?: TelephoneConfig })?.config ?? null;
    } catch {
        ToastUtils.error(t("call.greeting_generated_failed"));
        return null;
    }
}

export async function executeGenerateGreeting(data?: Record<string, unknown>): Promise<boolean> {
    try {
        await generateVoicemailGreeting(data);
        ToastUtils.success(t("call.greeting_generated_success"));
        return true;
    } catch {
        ToastUtils.error(t("call.greeting_generated_failed"));
        return false;
    }
}

export async function executeUploadGreeting(file: File): Promise<boolean> {
    try {
        await uploadVoicemailGreeting(file);
        ToastUtils.success(t("call.greeting_uploaded_success"));
        return true;
    } catch {
        ToastUtils.error(t("call.greeting_uploaded_failed"));
        return false;
    }
}

export async function executeDeleteGreeting(): Promise<boolean> {
    if (!(await DialogUtils.confirm(t("call.delete_greeting_confirm")))) return false;
    try {
        await deleteVoicemailGreeting();
        ToastUtils.success(t("call.greeting_deleted_success"));
        return true;
    } catch {
        ToastUtils.error(t("call.greeting_deleted_failed"));
        return false;
    }
}

export async function executeStartRecordingGreetingMic(): Promise<boolean> {
    try {
        await startRecordingGreetingMic();
        ToastUtils.info(t("call.recording_greeting_started"));
        return true;
    } catch {
        ToastUtils.error(t("call.recording_greeting_failed"));
        return false;
    }
}

export async function executeStopRecordingGreetingMic(): Promise<boolean> {
    try {
        await stopRecordingGreetingMic();
        ToastUtils.success(t("call.recording_greeting_stopped"));
        return true;
    } catch {
        ToastUtils.error(t("call.recording_greeting_failed"));
        return false;
    }
}

export async function executeDeleteVoicemail(voicemailId: number | string): Promise<boolean> {
    if (!(await DialogUtils.confirm(t("call.delete_voicemail_confirm")))) return false;
    try {
        await deleteVoicemail(voicemailId);
        ToastUtils.success(t("call.voicemail_deleted_success"));
        return true;
    } catch {
        ToastUtils.error(t("call.voicemail_deleted_failed"));
        return false;
    }
}

export async function executeMarkVoicemailRead(
    voicemail: Partial<Voicemail> & { id: number | string }
): Promise<boolean> {
    if (voicemail.is_read) return true;
    try {
        await markVoicemailAsRead(voicemail.id);
        voicemail.is_read = true;
        return true;
    } catch {
        return false;
    }
}

export async function executeDeleteRecording(recordingId: number | string): Promise<boolean> {
    if (!(await DialogUtils.confirm(t("call.delete_recording_confirm")))) return false;
    try {
        await deleteRecording(recordingId);
        ToastUtils.success(t("call.recording_deleted_success"));
        return true;
    } catch {
        ToastUtils.error(t("call.recording_deleted_failed"));
        return false;
    }
}
