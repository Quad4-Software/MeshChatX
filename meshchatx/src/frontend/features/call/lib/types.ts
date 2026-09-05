// SPDX-License-Identifier: 0BSD

import type { CALL_TAB_IDS } from "./constants.js";

/**
 * Valid active tab identifier in the Call page
 */
export type CallTabId = (typeof CALL_TAB_IDS)[number];

/**
 * LXMF user icon presentation metadata
 */
export interface UserIconMetadata {
    icon_name?: string;
    foreground_colour?: string;
    background_colour?: string;
}

/**
 * Currently active telephone call
 */
export interface ActiveCall {
    hash: string;
    remote_identity_hash: string;
    remote_destination_hash?: string;
    remote_identity_name?: string | null;
    remote_icon?: UserIconMetadata | null;
    custom_image?: string | null;
    is_incoming?: boolean;
    status: number;
    remote_telephony_hash?: string;
    audio_profile_id?: number | null;
    call_mode_id?: number;
    call_mode_name?: string;
    call_mode_abbrev?: string;
    is_half_duplex?: boolean;
    is_ptt_active?: boolean;
    is_transmit_squelched?: boolean;
    is_mic_muted?: boolean;
    is_speaker_muted?: boolean;
    is_recording?: boolean;
    is_voicemail?: boolean;
    call_start_time?: number | null;
    is_contact?: boolean;
    tx_bytes?: number;
    rx_bytes?: number;
    tx_packets?: number;
    rx_packets?: number;
    tx_bps?: number;
    rx_bps?: number;
    path_hops?: number | null;
    path_interface?: string | null;
}

/**
 * Telephone call history row
 */
export interface CallHistoryEntry {
    id?: number;
    hash?: string;
    remote_identity_hash: string;
    remote_identity_name?: string;
    remote_destination_hash?: string;
    remote_telephony_hash?: string;
    remote_icon?: UserIconMetadata | null;
    contact_image?: string | null;
    custom_image?: string | null;
    is_incoming?: boolean;
    status?: number;
    duration?: number;
    created_at?: string;
    call_start_time?: number;
    is_missed?: boolean;
}

/**
 * Telephone contact entry
 */
export interface TelephoneContact {
    id?: number;
    name: string;
    remote_identity_hash: string;
    lxmf_address?: string;
    lxst_address?: string;
    remote_destination_hash?: string;
    remote_telephony_hash?: string;
    preferred_ringtone_id?: number | null;
    custom_image?: string | null;
    clear_image?: boolean;
    is_telemetry_trusted?: number | boolean;
    remote_icon?: UserIconMetadata | null;
    created_at?: string;
    updated_at?: string;
}

/**
 * Recorded voicemail item
 */
export interface Voicemail {
    id: number;
    remote_identity_hash: string;
    remote_identity_name?: string;
    remote_destination_hash?: string;
    remote_telephony_hash?: string;
    remote_icon?: UserIconMetadata | null;
    contact_image?: string | null;
    custom_image?: string | null;
    duration?: number;
    is_read: number | boolean;
    created_at: string;
}

/**
 * Voicemail service status
 */
export interface VoicemailStatus {
    has_espeak: boolean;
    is_recording: boolean;
    is_greeting_recording: boolean;
    has_greeting: boolean;
}

/**
 * Ringtone audio record
 */
export interface Ringtone {
    id: number;
    filename: string;
    storage_filename?: string;
    display_name: string;
    is_primary: boolean;
    created_at?: string;
    [key: string]: unknown;
}

/**
 * Ringtone service status
 */
export interface RingtoneStatus {
    has_custom_ringtone?: boolean;
    enabled?: boolean;
    filename?: string | null;
    id?: number | null;
    volume?: number;
    [key: string]: unknown;
}

/**
 * Saved call recording item
 */
export interface Recording {
    id: number;
    remote_identity_hash: string;
    remote_identity_name?: string;
    remote_icon?: UserIconMetadata | null;
    filename_rx?: string;
    filename_tx?: string;
    duration?: number;
    created_at: string;
    [key: string]: unknown;
}

/**
 * Audio codec profile
 */
export interface AudioProfile {
    id: number;
    name: string;
    available: boolean;
    unavailable_reason?: string;
}

/**
 * Response payload for audio profiles query
 */
export interface AudioProfilesResponse {
    default_audio_profile_id?: number;
    codec2_available?: boolean;
    audio_profiles: AudioProfile[];
}

/**
 * Call mode definition (full duplex vs half duplex)
 */
export interface CallMode {
    id: number;
    name: string;
    abbrev: string;
    is_half_duplex: boolean;
}

/**
 * Response payload for call modes query
 */
export interface CallModesResponse {
    default_call_mode_id?: number;
    call_modes: CallMode[];
}

/**
 * Web Audio bridge runtime status
 */
export interface WebAudioStatus {
    enabled?: boolean;
    required?: boolean;
    allow_fallback?: boolean;
    has_client?: boolean;
    frame_ms?: number | null;
    diagnostics?: Record<string, unknown>;
}

/**
 * Telephony subsystem status
 */
export interface TelephoneStatus {
    enabled: boolean;
    message?: string;
    is_busy?: boolean;
    call_status?: number;
    active_call?: ActiveCall | null;
    is_mic_muted?: boolean;
    is_speaker_muted?: boolean;
    preferred_call_mode_id?: number;
    missed_calls_unread_count?: number;
    voicemail?: {
        is_recording?: boolean;
        unread_count?: number;
        latest_id?: number | null;
    };
    initiation_status?: string | null;
    initiation_target_hash?: string | null;
    initiation_target_name?: string | null;
    web_audio?: WebAudioStatus;
}

/**
 * Global configuration slice relevant to telephone
 */
export interface TelephoneConfig {
    telephone_enabled?: boolean;
    telephone_web_audio_enabled?: boolean;
    telephone_web_audio_allow_fallback?: boolean;
    telephone_call_mode_id?: number;
    telephone_allow_calls_from_contacts_only?: boolean;
    telephone_announce_enabled?: boolean;
    call_recording_enabled?: boolean;
    do_not_disturb_enabled?: boolean;
    voicemail_enabled?: boolean;
    voicemail_greeting?: string;
    voicemail_tts_speed?: number;
    voicemail_tts_pitch?: number;
    voicemail_tts_word_gap?: number;
    voicemail_tts_voice?: string;
    voicemail_auto_answer_delay_seconds?: number;
    voicemail_max_recording_seconds?: number;
    ringtone_preferred_id?: number | null;
    custom_ringtone_enabled?: boolean;
    ringtone_volume?: number;
    telephone_tone_generator_enabled?: boolean;
    telephone_tone_generator_volume?: number;
    [key: string]: unknown;
}

/**
 * Autocomplete suggestion when entering a destination to call
 */
export interface CallSuggestion {
    name: string;
    hash: string;
    type: "contact" | "history";
    icon: string;
}

/**
 * Media device representation
 */
export interface AudioDeviceItem {
    deviceId: string;
    kind: "audioinput" | "audiooutput" | MediaDeviceKind;
    label: string;
    groupId: string;
}

/**
 * Discovery announce item for telephony peers
 */
export interface DiscoveryAnnounce {
    destination_hash: string;
    identity_hash?: string;
    display_name?: string;
    lxmf_destination_hash?: string;
    updated_at?: string;
    hops?: number | null;
    contact_image?: string | null;
    lxmf_user_icon?: UserIconMetadata | null;
}

/**
 * Response payload for announces query
 */
export interface DiscoveryResponse {
    announces?: DiscoveryAnnounce[];
    total_count?: number;
}

/**
 * Response payload for call history query
 */
export interface HistoryResponse {
    call_history?: CallHistoryEntry[];
    total_count?: number;
}

/**
 * Response payload for voicemails query
 */
export interface VoicemailsResponse {
    voicemails?: Voicemail[];
    unread_count?: number;
}

/**
 * Response payload for recordings query
 */
export interface RecordingsResponse {
    recordings?: Recording[];
}

/**
 * Response payload for contacts query
 */
export interface ContactsResponse {
    contacts?: TelephoneContact[];
    total_count?: number;
}

/**
 * Response payload after switching call mode
 */
export interface SwitchCallModeResponse {
    message?: string;
    mode_id?: number;
    mode_name?: string;
    is_half_duplex?: boolean;
    is_ptt_active?: boolean;
}

/**
 * Response payload after switching audio profile
 */
export interface SwitchAudioProfileResponse {
    message?: string;
    profile_id?: number;
    remapped?: boolean;
}

/**
 * Response payload after updating PTT state
 */
export interface PttResponse {
    message?: string;
    is_ptt_active?: boolean;
    is_half_duplex?: boolean;
    is_transmit_squelched?: boolean;
}

/**
 * Response payload after initiating a call
 */
export interface CallInitiationResponse {
    message?: string;
}

/**
 * Response payload after generating a greeting
 */
export interface GenerateGreetingResponse {
    message?: string;
    path?: string;
}
