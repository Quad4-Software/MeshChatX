// SPDX-License-Identifier: 0BSD

import GlobalEmitter from "../../../js/GlobalEmitter.js";
import GlobalState from "../../../js/GlobalState.js";
import { t } from "../../../js/i18n.js";
import ToastUtils from "../../../js/ToastUtils.js";
import {
    fetchAudioProfiles,
    fetchCallHistory,
    fetchCallModes,
    fetchConfig,
    fetchContacts,
    fetchDiscoveryAnnounces,
    fetchRecordings,
    fetchRingtones,
    fetchRingtoneStatus,
    fetchVoicemails,
    fetchVoicemailStatus,
    markMissedCallsViewed,
} from "./callApi.js";
import { CallStatusPoller } from "./callStatusPoll.js";
import { CallWebAudioBridge } from "./callWebAudio.js";
import { DEFAULT_CALL_HISTORY_LIMIT, DEFAULT_DISCOVERY_LIMIT, DEFAULT_VOICEMAIL_LIMIT } from "./constants.js";
import type { RingtoneItem } from "./ringtoneEditorLogic.js";
import type {
    ActiveCall,
    AudioProfile,
    CallHistoryEntry,
    CallMode,
    DiscoveryAnnounce,
    Recording,
    Ringtone,
    TelephoneConfig,
    TelephoneContact,
    Voicemail,
    VoicemailStatus,
    WebAudioStatus,
} from "./types.js";

/**
 * Checks if keyboard event target is an editable form element
 */
export function isEditableEventTarget(target: EventTarget | null): boolean {
    if (!target || !(target instanceof Element)) return false;
    const tag = (target.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select") return true;
    return Boolean((target as HTMLElement).isContentEditable);
}

export interface CallAudioPlayerState {
    playingVoicemailId: string | number | null;
    playingRingtoneId: number | string | null;
    playingRecordingId: string | number | null;
    playingSide: "rx" | "tx" | null;
    isPlayingGreeting: boolean;
    isPlayingRingtone: boolean;
}

/**
 * Manages audio previews for ringtones greetings and recordings
 */
export class CallAudioPlayerManager {
    private player: HTMLAudioElement | null = null;
    public state: CallAudioPlayerState = {
        playingVoicemailId: null,
        playingRingtoneId: null,
        playingRecordingId: null,
        playingSide: null,
        isPlayingGreeting: false,
        isPlayingRingtone: false,
    };

    public stopAll(): void {
        if (this.player) {
            try {
                this.player.pause();
                this.player.src = "";
            } catch {
                // ignore
            }
            this.player = null;
        }
        this.state.playingVoicemailId = null;
        this.state.playingRingtoneId = null;
        this.state.playingRecordingId = null;
        this.state.playingSide = null;
        this.state.isPlayingGreeting = false;
        this.state.isPlayingRingtone = false;
    }

    public async playRingtone(ringtone: Ringtone | RingtoneItem, volumePercent: number = 100): Promise<void> {
        if (this.state.isPlayingRingtone && this.state.playingRingtoneId === ringtone.id) {
            this.stopAll();
            return;
        }
        this.stopAll();
        this.state.playingRingtoneId = ringtone.id;
        this.state.isPlayingRingtone = true;
        const audio = new Audio(`/api/v1/telephone/ringtones/${ringtone.id}/audio`);
        audio.volume = Math.max(0, Math.min(1, volumePercent / 100.0));
        audio.onended = () => this.stopAll();
        audio.onerror = () => {
            ToastUtils.error(t("call.failed_to_play_ringtone"));
            this.stopAll();
        };
        this.player = audio;
        try {
            await audio.play();
        } catch {
            ToastUtils.error(t("call.failed_to_play_ringtone"));
            this.stopAll();
        }
    }

    public async playGreeting(): Promise<void> {
        if (this.state.isPlayingGreeting) {
            this.stopAll();
            return;
        }
        this.stopAll();
        this.state.isPlayingGreeting = true;
        const audio = new Audio("/api/v1/telephone/voicemail/greeting/audio");
        audio.onended = () => this.stopAll();
        audio.onerror = () => {
            ToastUtils.error(t("call.no_greeting_audio_found"));
            this.stopAll();
        };
        this.player = audio;
        try {
            await audio.play();
        } catch {
            ToastUtils.error(t("call.no_greeting_audio_found"));
            this.stopAll();
        }
    }

    public async playVoicemail(voicemail: { id: string | number }): Promise<boolean> {
        if (this.state.playingVoicemailId === voicemail.id) {
            this.stopAll();
            return false;
        }
        this.stopAll();
        this.state.playingVoicemailId = voicemail.id;
        const audio = new Audio(`/api/v1/telephone/voicemails/${encodeURIComponent(String(voicemail.id))}/audio`);
        audio.onended = () => this.stopAll();
        audio.onerror = () => {
            ToastUtils.error(t("call.failed_to_play_voicemail"));
            this.stopAll();
        };
        this.player = audio;
        try {
            await audio.play();
            return true;
        } catch {
            ToastUtils.error(t("call.failed_to_play_voicemail"));
            this.stopAll();
            return false;
        }
    }

    public async playRecording(recording: Recording, side: "rx" | "tx"): Promise<void> {
        if (this.state.playingRecordingId === recording.id && this.state.playingSide === side) {
            this.stopAll();
            return;
        }
        this.stopAll();
        this.state.playingRecordingId = recording.id;
        this.state.playingSide = side;
        const audio = new Audio(`/api/v1/telephone/recordings/${recording.id}/audio/${side}`);
        audio.onended = () => this.stopAll();
        audio.onerror = () => {
            ToastUtils.error(t("call.failed_to_load_recording"));
            this.stopAll();
        };
        this.player = audio;
        try {
            await audio.play();
        } catch {
            ToastUtils.error(t("call.failed_to_load_recording"));
            this.stopAll();
        }
    }
}

/**
 * Controller orchestrating background tasks timers and event listeners for the Call page
 */
export class CallPageController {
    public poller: CallStatusPoller;
    public webAudio: CallWebAudioBridge;
    public audioPlayer: CallAudioPlayerManager;
    public isPopout: () => boolean;
    private listenersBound = false;
    private onHistoryUpdatedBound: () => void;
    private onWsReconnectedBound: () => void;
    private pttKeyDownBound: (e: KeyboardEvent) => void;
    private pttKeyUpBound: (e: KeyboardEvent) => void;
    private pttWindowBlurBound: () => void;

    constructor(options: {
        onPollStatus: () => Promise<void>;
        onPollHistory: () => Promise<void>;
        onElapsedTick: () => void;
        onPttSpaceDown: () => void;
        onPttSpaceUp: () => void;
        onPttBlur: () => void;
        onConfigDisableWebAudio?: () => Promise<void>;
        isPopout?: boolean | (() => boolean);
    }) {
        this.isPopout = typeof options.isPopout === "function" ? options.isPopout : () => Boolean(options.isPopout);
        this.audioPlayer = new CallAudioPlayerManager();
        this.webAudio = new CallWebAudioBridge({
            callbacks: {
                onConfigDisable: options.onConfigDisableWebAudio,
            },
        });
        this.poller = new CallStatusPoller({
            onPollStatus: options.onPollStatus,
            onPollHistory: options.onPollHistory,
            onElapsedTick: options.onElapsedTick,
            isLiveTransportReady: () => Boolean(GlobalState.liveTransportReady),
        });

        this.onHistoryUpdatedBound = () => {
            options.onPollHistory();
            markMissedCallsViewed().catch(() => {});
        };
        this.onWsReconnectedBound = () => {
            options.onPollStatus();
            options.onPollHistory();
        };
        this.pttKeyDownBound = (e: KeyboardEvent) => {
            if (e.code !== "Space" && e.key !== " ") return;
            if (e.repeat || isEditableEventTarget(e.target)) return;
            options.onPttSpaceDown();
        };
        this.pttKeyUpBound = (e: KeyboardEvent) => {
            if (e.code !== "Space" && e.key !== " ") return;
            options.onPttSpaceUp();
        };
        this.pttWindowBlurBound = () => {
            options.onPttBlur();
        };
    }

    public bindListeners(): void {
        if (this.listenersBound) return;
        this.listenersBound = true;
        GlobalEmitter.on("telephone-history-updated", this.onHistoryUpdatedBound);
        GlobalEmitter.on("websocket-reconnected", this.onWsReconnectedBound);
        if (typeof window !== "undefined") {
            window.addEventListener("keydown", this.pttKeyDownBound);
            window.addEventListener("keyup", this.pttKeyUpBound);
            window.addEventListener("blur", this.pttWindowBlurBound);
        }
        this.poller.startAll();
    }

    public unbindListeners(): void {
        if (!this.listenersBound) return;
        this.listenersBound = false;
        GlobalEmitter.off("telephone-history-updated", this.onHistoryUpdatedBound);
        GlobalEmitter.off("websocket-reconnected", this.onWsReconnectedBound);
        if (typeof window !== "undefined") {
            window.removeEventListener("keydown", this.pttKeyDownBound);
            window.removeEventListener("keyup", this.pttKeyUpBound);
            window.removeEventListener("blur", this.pttWindowBlurBound);
        }
        this.poller.stopAll();
        this.audioPlayer.stopAll();
        this.webAudio.stop();
    }

    public async ensureWebAudio(webAudioStatus?: WebAudioStatus, activeCall?: ActiveCall | null): Promise<void> {
        if (!webAudioStatus?.enabled || activeCall?.is_voicemail) {
            this.webAudio.stop();
            return;
        }
        if (activeCall && webAudioStatus.enabled) {
            this.webAudio.audioFrameMs = webAudioStatus.frame_ms || 60;
            await this.webAudio.start();
        } else {
            this.webAudio.stop();
        }
    }
}

/**
 * Loads bootstrap data for the call page
 */
export async function loadCallBootstrapData(): Promise<{
    config: TelephoneConfig | null;
    audioProfiles: AudioProfile[];
    defaultProfileId?: number | string;
    callModes: CallMode[];
    defaultCallModeId?: number | string;
    voicemailStatus: VoicemailStatus;
    ringtones: Ringtone[];
}> {
    let config: TelephoneConfig | null = null;
    let audioProfiles: AudioProfile[] = [];
    let defaultProfileId: number | string | undefined;
    let callModes: CallMode[] = [];
    let defaultCallModeId: number | string | undefined;
    let voicemailStatus: VoicemailStatus = {
        has_espeak: false,
        is_recording: false,
        is_greeting_recording: false,
        has_greeting: false,
    };
    let ringtones: Ringtone[] = [];

    try {
        const [cfgRes, profRes, modeRes, vmStatRes, rtRes] = await Promise.all([
            fetchConfig().catch(() => null),
            fetchAudioProfiles().catch(() => null),
            fetchCallModes().catch(() => null),
            fetchVoicemailStatus().catch(() => null),
            fetchRingtones().catch(() => null),
        ]);
        if (cfgRes?.config) config = cfgRes.config;
        if (profRes) {
            audioProfiles = profRes.audio_profiles || [];
            defaultProfileId = profRes.default_audio_profile_id;
        }
        if (modeRes) {
            callModes = modeRes.call_modes || [];
            defaultCallModeId = modeRes.default_call_mode_id;
        }
        if (vmStatRes) voicemailStatus = vmStatRes;
        if (Array.isArray(rtRes)) ringtones = rtRes;
        await fetchRingtoneStatus().catch(() => {});
        await markMissedCallsViewed().catch(() => {});
    } catch (e) {
        console.error(e);
    }

    return {
        config,
        audioProfiles,
        defaultProfileId,
        callModes,
        defaultCallModeId,
        voicemailStatus,
        ringtones,
    };
}

/**
 * Fetches call history entries with pagination
 */
export async function loadCallHistoryData(options: {
    offset: number;
    search: string;
    limit?: number;
}): Promise<{ entries: CallHistoryEntry[]; totalCount: number }> {
    try {
        const res = await fetchCallHistory({
            limit: options.limit ?? DEFAULT_CALL_HISTORY_LIMIT,
            offset: options.offset,
            search: options.search,
        });
        return {
            entries: res.call_history || [],
            totalCount: res.total_count ?? 0,
        };
    } catch {
        return { entries: [], totalCount: 0 };
    }
}

/**
 * Fetches discovery announces with pagination
 */
export async function loadDiscoveryData(options: {
    offset: number;
    search: string;
    limit?: number;
}): Promise<{ announces: DiscoveryAnnounce[]; totalCount: number }> {
    try {
        const res = await fetchDiscoveryAnnounces({
            limit: options.limit ?? DEFAULT_DISCOVERY_LIMIT,
            offset: options.offset,
            search: options.search,
        });
        return {
            announces: res.announces || [],
            totalCount: res.total_count ?? 0,
        };
    } catch {
        return { announces: [], totalCount: 0 };
    }
}

/**
 * Fetches voicemails and unread count
 */
export async function loadVoicemailsData(search: string): Promise<{
    voicemails: Voicemail[];
    unreadCount: number;
}> {
    try {
        const res = await fetchVoicemails({
            search,
            limit: DEFAULT_VOICEMAIL_LIMIT,
        });
        return {
            voicemails: res.voicemails || [],
            unreadCount: res.unread_count || 0,
        };
    } catch {
        return { voicemails: [], unreadCount: 0 };
    }
}

/**
 * Fetches contacts list
 */
export async function loadContactsData(search: string): Promise<TelephoneContact[]> {
    try {
        const res = await fetchContacts({ search });
        return Array.isArray(res) ? res : res.contacts || [];
    } catch {
        return [];
    }
}

/**
 * Fetches recordings list
 */
export async function loadRecordingsData(search: string): Promise<Recording[]> {
    try {
        const res = await fetchRecordings({ search });
        return res.recordings || [];
    } catch {
        return [];
    }
}
