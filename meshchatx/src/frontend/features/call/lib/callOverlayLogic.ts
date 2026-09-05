// SPDX-License-Identifier: 0BSD

import Utils from "../../../js/Utils.js";
import ToastUtils from "../../../js/ToastUtils.js";
import { t } from "../../../js/i18n.js";
import { promptMicrophoneAccessFromWindow } from "../../../js/webAudioMicPermission.js";

export interface CallRemoteIcon {
    icon_name?: string;
    foreground_colour?: string;
    background_colour?: string;
}

export interface ActiveCall {
    hash?: string;
    remote_identity_hash?: string | null;
    remote_identity_name?: string | null;
    status?: number;
    is_incoming?: boolean;
    is_voicemail?: boolean;
    is_recording?: boolean;
    is_contact?: boolean;
    is_mic_muted?: boolean;
    is_speaker_muted?: boolean;
    is_ptt_active?: boolean;
    is_half_duplex?: boolean;
    call_start_time?: number | null;
    tx_bytes?: number;
    rx_bytes?: number;
    custom_image?: string | null;
    remote_icon?: CallRemoteIcon | null;
    [key: string]: unknown;
}

export interface VoicemailStatus {
    latest_id?: string | number | null;
    is_recording?: boolean;
    [key: string]: unknown;
}

export interface RouterLike {
    push?: (target: { name?: string; path?: string; query?: Record<string, string> }) => Promise<unknown> | void;
}

export interface RouteLike {
    name?: string;
    query?: Record<string, string>;
}

export interface CallOverlayProps {
    activeCall?: ActiveCall | null;
    isEnded?: boolean;
    wasDeclined?: boolean;
    voicemailStatus?: VoicemailStatus | null;
    initiationStatus?: string | null;
    initiationTargetHash?: string | null;
    initiationTargetName?: string | null;
    activeCallTab?: string | null;
    elapsedTime?: string | null;
    callDuration?: string | null;
    isMinimized?: boolean;
    router?: RouterLike;
    route?: RouteLike;
    onanswer?: () => void | Promise<void>;
    onhangup?: () => void | Promise<void>;
    onmute?: (muted: boolean) => void | Promise<void>;
    ontogglemic?: (muted: boolean) => void | Promise<void>;
    ontogglespeaker?: (muted: boolean) => void | Promise<void>;
    onexpand?: () => void;
    ongotophone?: () => void;
}

const KNOWN_INITIATION_STATUSES = new Set([
    "Initiating...",
    "Resolving identity...",
    "Discovering path/identity...",
    "Requesting path...",
    "Dialing...",
    "Calling...",
    "Ringing...",
    "Establishing link...",
]);

export function getHeaderStatusText(params: {
    wasDeclined?: boolean;
    isEnded?: boolean;
    activeCall?: ActiveCall | null;
    initiationStatus?: string | null;
}): string {
    const { wasDeclined, isEnded, activeCall, initiationStatus } = params;

    if (wasDeclined) {
        return t("call.call_declined");
    }
    if (isEnded) {
        return t("call.call_ended");
    }
    if (activeCall?.is_voicemail) {
        return t("call.recording_voicemail");
    }
    if (activeCall?.status === 6) {
        return t("call.active_call");
    }
    if (initiationStatus) {
        if (KNOWN_INITIATION_STATUSES.has(initiationStatus)) {
            return initiationStatus;
        }
        return t("call.initiation");
    }
    return t("call.call_status");
}

export function getCallStatusLabel(params: {
    activeCall?: ActiveCall | null;
    wasDeclined?: boolean;
    isEnded?: boolean;
}): string {
    const { activeCall, wasDeclined, isEnded } = params;
    if (wasDeclined) {
        return t("call.call_declined");
    }
    if (isEnded) {
        return t("call.call_ended");
    }
    if (!activeCall) {
        return "";
    }
    if (activeCall.is_voicemail) {
        return t("call.recording_voicemail");
    }
    if (activeCall.is_incoming && activeCall.status === 4) {
        return t("call.incoming_call");
    }
    switch (activeCall.status) {
        case 0:
            return t("call.busy");
        case 1:
            return t("call.rejected");
        case 2:
            return t("call.calling");
        case 3:
            return t("call.available");
        case 4:
            return t("call.ringing");
        case 5:
            return t("call.establishing_link");
        case 6:
            return t("call.connected");
        default:
            return `${t("call.status")}: ${activeCall.status}`;
    }
}

export function formatDestinationHash(hash?: string | null): string {
    if (!hash) {
        return "";
    }
    return Utils.formatDestinationHash(hash);
}

export function formatBytes(bytes?: number | null): string {
    return Utils.formatBytes(bytes || 0);
}

export function formatMinutesSeconds(seconds: number): string {
    return Utils.formatMinutesSeconds(seconds);
}

export function calculateElapsedTime(startTime?: number | null, nowMs?: number): string | null {
    if (!startTime) {
        return null;
    }
    const currentMs = nowMs ?? Date.now();
    const elapsed = Math.floor(currentMs / 1000 - startTime);
    return Utils.formatMinutesSeconds(elapsed);
}

export function calculateCallDuration(isEnded?: boolean, startTime?: number | null, nowMs?: number): string | null {
    if (!isEnded || !startTime) {
        return null;
    }
    const currentMs = nowMs ?? Date.now();
    const duration = Math.floor(currentMs / 1000 - startTime);
    return Utils.formatMinutesSeconds(duration);
}

export function getStatusColorClass(params: {
    wasDeclined?: boolean;
    isEnded?: boolean;
    activeCall?: ActiveCall | null;
}): string {
    const { wasDeclined, isEnded, activeCall } = params;
    if (isEnded || wasDeclined || activeCall?.is_voicemail) {
        return "text-red-600 dark:text-red-400 animate-pulse";
    }
    if (activeCall?.status === 6) {
        return "text-green-600 dark:text-green-400";
    }
    return "text-sem-fg-muted";
}

export async function executeAnswerCall(params: {
    router?: RouterLike;
    route?: RouteLike;
    onanswer?: () => void | Promise<void>;
    ongotophone?: () => void;
}): Promise<void> {
    try {
        try {
            await promptMicrophoneAccessFromWindow();
        } catch {
            /* Mic error handled after navigation */
        }
        const api = (window as unknown as { api: { post: (url: string, data?: unknown) => Promise<unknown> } }).api;
        await api.post("/api/v1/telephone/answer");
        if (params.onanswer) {
            await params.onanswer();
        }
        if (params.ongotophone) {
            params.ongotophone();
        } else if (params.router?.push) {
            if (params.route?.name !== "call" || params.route?.query?.tab !== "phone") {
                await params.router.push({ name: "call", query: { tab: "phone" } });
            }
        }
    } catch {
        ToastUtils.error(t("call.failed_to_answer_call"));
    }
}

export async function executeHangupCall(params: {
    onhangup?: () => void | Promise<void>;
}): Promise<void> {
    try {
        if (params.onhangup) {
            await params.onhangup();
        }
        const api = (window as unknown as { api: { post: (url: string, data?: unknown) => Promise<unknown> } }).api;
        await api.post("/api/v1/telephone/hangup");
    } catch {
        ToastUtils.error(t("call.failed_to_hangup_call"));
    }
}

export async function executeSendToVoicemail(): Promise<void> {
    try {
        const api = (window as unknown as { api: { post: (url: string, data?: unknown) => Promise<unknown> } }).api;
        await api.post("/api/v1/telephone/send-to-voicemail");
        ToastUtils.success(t("call.call_sent_to_voicemail"));
    } catch {
        ToastUtils.error(t("call.failed_to_send_to_voicemail"));
    }
}

export async function executeToggleMicrophone(params: {
    isCurrentlyMuted: boolean;
    onmute?: (muted: boolean) => void | Promise<void>;
    ontogglemic?: (muted: boolean) => void | Promise<void>;
}): Promise<boolean> {
    const nextMuted = !params.isCurrentlyMuted;
    try {
        if (params.onmute) params.onmute(nextMuted);
        if (params.ontogglemic) params.ontogglemic(nextMuted);
        const endpoint = params.isCurrentlyMuted
            ? "/api/v1/telephone/unmute-transmit"
            : "/api/v1/telephone/mute-transmit";
        const api = (window as unknown as { api: { post: (url: string, data?: unknown) => Promise<unknown> } }).api;
        await api.post(endpoint);
        return nextMuted;
    } catch {
        ToastUtils.error(t("call.failed_to_toggle_microphone"));
        return params.isCurrentlyMuted;
    }
}

export async function executeToggleSpeaker(params: {
    isCurrentlyMuted: boolean;
    ontogglespeaker?: (muted: boolean) => void | Promise<void>;
}): Promise<boolean> {
    const nextMuted = !params.isCurrentlyMuted;
    try {
        if (params.ontogglespeaker) params.ontogglespeaker(nextMuted);
        const endpoint = params.isCurrentlyMuted
            ? "/api/v1/telephone/unmute-receive"
            : "/api/v1/telephone/mute-receive";
        const api = (window as unknown as { api: { post: (url: string, data?: unknown) => Promise<unknown> } }).api;
        await api.post(endpoint);
        return nextMuted;
    } catch {
        ToastUtils.error(t("call.failed_to_toggle_speaker"));
        return params.isCurrentlyMuted;
    }
}

export async function executeToggleDuplexMode(
    activeCall?: ActiveCall | null,
    isHalfDuplex?: boolean
): Promise<{ isPttActive: boolean; isHalfDuplex: boolean } | null> {
    if (!activeCall || activeCall.status !== 6) return null;
    const nextMode = isHalfDuplex ? 1 : 2;
    try {
        const api = (window as unknown as {
            api: { post: (url: string, data?: unknown) => Promise<{ data?: { is_ptt_active?: boolean; is_half_duplex?: boolean } }> };
        }).api;
        const response = await api.post(`/api/v1/telephone/switch-call-mode/${nextMode}`);
        return {
            isPttActive: Boolean(response.data?.is_ptt_active),
            isHalfDuplex: Boolean(response.data?.is_half_duplex),
        };
    } catch {
        ToastUtils.error(t("call.failed_to_switch_call_mode"));
        return null;
    }
}

export async function executeSetPttActive(
    active: boolean,
    activeCall?: ActiveCall | null,
    isHalfDuplex?: boolean
): Promise<boolean> {
    if (!activeCall || activeCall.status !== 6 || !isHalfDuplex) {
        return false;
    }
    const wantActive = Boolean(active);
    try {
        const api = (window as unknown as { api: { post: (url: string, data?: unknown) => Promise<unknown> } }).api;
        await api.post("/api/v1/telephone/ptt", { active: wantActive });
        return wantActive;
    } catch {
        if (wantActive) {
            ToastUtils.error(t("call.failed_to_set_ptt"));
        }
        return !wantActive;
    }
}
