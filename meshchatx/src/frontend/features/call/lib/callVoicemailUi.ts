// SPDX-License-Identifier: 0BSD

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

/**
 * Resolves the destination hash to use when calling back from a voicemail
 */
export function resolveCallbackHash(voicemail: VoicemailItem): string {
    return (
        voicemail.remote_telephony_hash ||
        voicemail.remote_destination_hash ||
        voicemail.remote_identity_hash ||
        ""
    );
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
