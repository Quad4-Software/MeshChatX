// SPDX-License-Identifier: 0BSD

import GlobalState from "../../../js/GlobalState.js";
import { fetchRingtones, fetchRingtoneStatus, fetchTelephoneStatus, fetchVoicemailStatus } from "./callApi.js";
import { executePatchConfig } from "./callPageActions.js";
import {
    CallPageController,
    loadCallBootstrapData,
    loadCallHistoryData,
    loadContactsData,
    loadDiscoveryData,
    loadRecordingsData,
    loadVoicemailsData,
} from "./callPageController.js";
import { hydrateContactVisuals } from "./callHistory.js";
import { CALL_ENDED_RESET_TIMEOUT_MS, DEFAULT_CALL_HISTORY_LIMIT, DEFAULT_DISCOVERY_LIMIT } from "./constants.js";
import type { RingtoneItem } from "./ringtoneEditorLogic.js";
import type {
    ActiveCall,
    AudioProfile,
    CallHistoryEntry,
    CallMode,
    DiscoveryAnnounce,
    Recording,
    Ringtone,
    RingtoneStatus,
    TelephoneConfig,
    TelephoneContact,
    Voicemail,
    VoicemailStatus,
} from "./types.js";

export interface CallPageState {
    config: TelephoneConfig | null;
    activeCall: ActiveCall | null;
    lastCall: ActiveCall | null;
    isCallEnded: boolean;
    wasDeclined: boolean;
    wasVoicemail: boolean;
    callMinimized: boolean;
    destinationHash: string;
    initiationStatus: string | null;
    initiationTargetHash: string | null;
    initiationTargetName: string | null;
    activeTab: string;
    unreadVoicemailsCount: number;
    webAudioBridgeRequired: boolean;
    audioProfiles: AudioProfile[];
    selectedAudioProfileId: number | string;
    callModes: CallMode[];
    selectedCallModeId: number | string;
    localMicMuted: boolean;
    localSpeakerMuted: boolean;
    localPttActive: boolean;
    pttKeyHeld: boolean;
    isMicMuting: boolean;
    isSpeakerMuting: boolean;
    callHistory: CallHistoryEntry[];
    callHistorySearch: string;
    callHistoryOffset: number;
    hasMoreCallHistory: boolean;
    isLoadingHistory: boolean;
    voicemails: Voicemail[];
    voicemailSearch: string;
    isLoadingVoicemails: boolean;
    voicemailStatus: VoicemailStatus;
    isGeneratingGreeting: boolean;
    isUploadingGreeting: boolean;
    contacts: TelephoneContact[];
    contactsSearch: string;
    isContactModalOpen: boolean;
    editingContact: TelephoneContact | null;
    contactForm: Partial<TelephoneContact>;
    discoveryAnnounces: DiscoveryAnnounce[];
    discoverySearch: string;
    totalDiscoveryCount: number;
    discoveryOffset: number;
    hasMoreDiscovery: boolean;
    isLoadingDiscovery: boolean;
    ringtones: Ringtone[];
    ringtoneStatus: RingtoneStatus;
    isUploadingRingtone: boolean;
    editingRingtoneId: number | string | null;
    editingRingtoneName: string;
    isRingtoneEditorOpen: boolean;
    editingRingtoneForAudio: Ringtone | RingtoneItem | Record<string, any> | null;
    recordings: Recording[];
    recordingSearch: string;
    isLoadingRecordings: boolean;
    nowSeconds: number;
}

export function createCallPageInitialState(): CallPageState {
    return {
        config: null,
        activeCall: null,
        lastCall: null,
        isCallEnded: false,
        wasDeclined: false,
        wasVoicemail: false,
        callMinimized: false,
        destinationHash: "",
        initiationStatus: null,
        initiationTargetHash: null,
        initiationTargetName: null,
        activeTab: "phone",
        unreadVoicemailsCount: 0,
        webAudioBridgeRequired: false,
        audioProfiles: [],
        selectedAudioProfileId: "",
        callModes: [],
        selectedCallModeId: 1,
        localMicMuted: false,
        localSpeakerMuted: false,
        localPttActive: false,
        pttKeyHeld: false,
        isMicMuting: false,
        isSpeakerMuting: false,
        callHistory: [],
        callHistorySearch: "",
        callHistoryOffset: 0,
        hasMoreCallHistory: false,
        isLoadingHistory: false,
        voicemails: [],
        voicemailSearch: "",
        isLoadingVoicemails: false,
        voicemailStatus: {
            has_espeak: false,
            is_recording: false,
            is_greeting_recording: false,
            has_greeting: false,
        },
        isGeneratingGreeting: false,
        isUploadingGreeting: false,
        contacts: [],
        contactsSearch: "",
        isContactModalOpen: false,
        editingContact: null,
        contactForm: {
            name: "",
            remote_identity_hash: "",
            lxmf_address: "",
            lxst_address: "",
            preferred_ringtone_id: null,
            custom_image: null,
        },
        discoveryAnnounces: [],
        discoverySearch: "",
        totalDiscoveryCount: 0,
        discoveryOffset: 0,
        hasMoreDiscovery: false,
        isLoadingDiscovery: false,
        ringtones: [],
        ringtoneStatus: {},
        isUploadingRingtone: false,
        editingRingtoneId: null,
        editingRingtoneName: "",
        isRingtoneEditorOpen: false,
        editingRingtoneForAudio: null,
        recordings: [],
        recordingSearch: "",
        isLoadingRecordings: false,
        nowSeconds: Date.now() / 1000,
    };
}

export class CallPageRuntime {
    public pageState: CallPageState;
    public controller: CallPageController;
    public getIsPopout: () => boolean;
    private endedTimeoutId: ReturnType<typeof setTimeout> | null = null;
    private searchDebounceId: ReturnType<typeof setTimeout> | null = null;
    public onPttTrigger?: (active: boolean) => Promise<void>;

    constructor(getIsPopout: () => boolean, initialCustomState?: CallPageState) {
        this.getIsPopout = getIsPopout;
        this.pageState = initialCustomState || createCallPageInitialState();
        this.controller = new CallPageController({
            onPollStatus: async () => {
                await this.getStatus();
                await this.getVoicemailStatus();
                await this.getRingtoneStatus();
            },
            onPollHistory: async () => {
                await this.getHistory();
                await this.getVoicemails();
                await this.getRecordings();
                await this.getContacts();
                await this.getDiscovery();
            },
            onElapsedTick: () => {
                this.pageState.nowSeconds = Date.now() / 1000;
            },
            onPttSpaceDown: () => {
                const isHalfDuplex = Boolean(
                    this.pageState.activeCall &&
                    this.pageState.activeCall.status === 6 &&
                    this.pageState.activeCall.is_half_duplex
                );
                if (!isHalfDuplex) return;
                this.pageState.pttKeyHeld = true;
                this.onPttTrigger?.(true);
            },
            onPttSpaceUp: () => {
                if (!this.pageState.pttKeyHeld && !this.pageState.localPttActive) return;
                this.pageState.pttKeyHeld = false;
                this.onPttTrigger?.(false);
            },
            onPttBlur: () => {
                this.pageState.pttKeyHeld = false;
                if (this.pageState.localPttActive) this.onPttTrigger?.(false);
            },
            onConfigDisableWebAudio: async () => {
                if (this.pageState.config) this.pageState.config.telephone_web_audio_enabled = false;
                await executePatchConfig({ telephone_web_audio_enabled: false });
            },
            isPopout: () => this.getIsPopout(),
        });
    }

    public hydrateVisuals(): void {
        const res = hydrateContactVisuals({
            contacts: this.pageState.contacts,
            activeCall: this.pageState.activeCall,
            lastCall: this.pageState.lastCall,
            callHistory: this.pageState.callHistory,
        });
        this.pageState.activeCall = res.activeCall || this.pageState.activeCall;
        this.pageState.lastCall = res.lastCall || this.pageState.lastCall;
        this.pageState.callHistory = res.callHistory;
    }

    public async getStatus(): Promise<void> {
        try {
            const res = await fetchTelephoneStatus();
            const oldCall = this.pageState.activeCall;
            const newCall = res.active_call || null;
            if (newCall) {
                if (!oldCall || newCall.hash !== oldCall.hash) {
                    this.pageState.localMicMuted = Boolean(newCall.is_mic_muted);
                    this.pageState.localSpeakerMuted = Boolean(newCall.is_speaker_muted);
                    this.pageState.localPttActive = Boolean(newCall.is_ptt_active);
                } else if (!this.pageState.isMicMuting && !this.pageState.isSpeakerMuting) {
                    this.pageState.localMicMuted = Boolean(
                        newCall.is_mic_muted ?? res.is_mic_muted ?? this.pageState.localMicMuted
                    );
                    this.pageState.localSpeakerMuted = Boolean(
                        newCall.is_speaker_muted ?? res.is_speaker_muted ?? this.pageState.localSpeakerMuted
                    );
                    if (!this.pageState.pttKeyHeld) this.pageState.localPttActive = Boolean(newCall.is_ptt_active);
                }
                if (newCall.call_mode_id != null) this.pageState.selectedCallModeId = newCall.call_mode_id;
            } else {
                this.pageState.localPttActive = false;
                this.pageState.pttKeyHeld = false;
            }
            this.pageState.activeCall = newCall;
            this.pageState.initiationStatus = res.initiation_status || null;
            this.pageState.initiationTargetHash = res.initiation_target_hash || null;
            this.pageState.initiationTargetName = res.initiation_target_name || null;
            if (this.pageState.activeCall?.is_voicemail) this.pageState.wasVoicemail = true;
            if (res.voicemail) this.pageState.unreadVoicemailsCount = res.voicemail.unread_count || 0;
            if (res.web_audio) {
                this.pageState.webAudioBridgeRequired = Boolean(res.web_audio.required);
                await this.controller.ensureWebAudio(res.web_audio, this.pageState.activeCall);
            }
            this.hydrateVisuals();
            if (oldCall != null && this.pageState.activeCall == null) {
                this.getHistory();
                this.getVoicemails();
                this.pageState.lastCall = oldCall;
                this.pageState.isCallEnded = true;
                if (this.endedTimeoutId) clearTimeout(this.endedTimeoutId);
                this.endedTimeoutId = setTimeout(() => {
                    this.pageState.isCallEnded = false;
                    this.pageState.lastCall = null;
                    if (this.getIsPopout() && typeof window !== "undefined") window.close();
                }, CALL_ENDED_RESET_TIMEOUT_MS);
            } else if (this.pageState.activeCall != null) {
                this.pageState.isCallEnded = false;
                this.pageState.wasDeclined = false;
                this.pageState.wasVoicemail = false;
                this.pageState.lastCall = null;
                if (this.endedTimeoutId) clearTimeout(this.endedTimeoutId);
            } else if (!this.endedTimeoutId) {
                this.pageState.isCallEnded = false;
                this.pageState.wasDeclined = false;
                this.pageState.wasVoicemail = false;
                this.pageState.lastCall = null;
            }
        } catch (e) {
            console.error(e);
        }
    }

    public async getHistory(loadMore = false): Promise<void> {
        if (!loadMore) this.pageState.callHistoryOffset = 0;
        this.pageState.isLoadingHistory = true;
        try {
            const res = await loadCallHistoryData({
                limit: DEFAULT_CALL_HISTORY_LIMIT,
                offset: this.pageState.callHistoryOffset,
                search: this.pageState.callHistorySearch,
            });
            this.pageState.callHistory = loadMore ? [...this.pageState.callHistory, ...res.entries] : res.entries;
            this.pageState.hasMoreCallHistory = res.totalCount > this.pageState.callHistory.length;
            this.hydrateVisuals();
        } finally {
            this.pageState.isLoadingHistory = false;
        }
    }

    public async getVoicemails(): Promise<void> {
        this.pageState.isLoadingVoicemails = true;
        try {
            const res = await loadVoicemailsData(this.pageState.voicemailSearch);
            this.pageState.voicemails = res.voicemails;
            this.pageState.unreadVoicemailsCount = res.unreadCount;
        } finally {
            this.pageState.isLoadingVoicemails = false;
        }
    }

    public async getVoicemailStatus(): Promise<void> {
        try {
            this.pageState.voicemailStatus = await fetchVoicemailStatus();
        } catch (e) {
            console.error(e);
        }
    }

    public async getContacts(): Promise<void> {
        this.pageState.contacts = await loadContactsData(this.pageState.contactsSearch);
        this.hydrateVisuals();
    }

    public async getDiscovery(loadMore = false): Promise<void> {
        if (!loadMore) this.pageState.discoveryOffset = 0;
        this.pageState.isLoadingDiscovery = true;
        try {
            const res = await loadDiscoveryData({
                limit: DEFAULT_DISCOVERY_LIMIT,
                offset: this.pageState.discoveryOffset,
                search: this.pageState.discoverySearch,
            });
            this.pageState.discoveryAnnounces = loadMore
                ? [...this.pageState.discoveryAnnounces, ...res.announces]
                : res.announces;
            this.pageState.totalDiscoveryCount = res.totalCount;
            this.pageState.hasMoreDiscovery =
                this.pageState.totalDiscoveryCount > this.pageState.discoveryAnnounces.length;
        } finally {
            this.pageState.isLoadingDiscovery = false;
        }
    }

    public async getRingtones(): Promise<void> {
        try {
            this.pageState.ringtones = await fetchRingtones();
        } catch (e) {
            console.error(e);
        }
    }

    public async getRingtoneStatus(): Promise<void> {
        try {
            this.pageState.ringtoneStatus = await fetchRingtoneStatus();
        } catch (e) {
            console.error(e);
        }
    }

    public async getRecordings(): Promise<void> {
        this.pageState.isLoadingRecordings = true;
        try {
            this.pageState.recordings = await loadRecordingsData(this.pageState.recordingSearch);
        } finally {
            this.pageState.isLoadingRecordings = false;
        }
    }

    public onTabChange = (tab: string): void => {
        this.pageState.activeTab = tab;
        GlobalState.activeCallTab = tab;
        if (tab === "recordings") this.getRecordings();
    };

    public debounceSearch(callback: () => void, delayMs = 300): void {
        if (this.searchDebounceId) clearTimeout(this.searchDebounceId);
        this.searchDebounceId = setTimeout(callback, delayMs);
    }

    public async mount(routeQuery: Record<string, string> = {}): Promise<void> {
        const boot = await loadCallBootstrapData();
        if (boot.config) this.pageState.config = boot.config;
        this.pageState.audioProfiles = boot.audioProfiles;
        if (boot.defaultProfileId != null) this.pageState.selectedAudioProfileId = boot.defaultProfileId;
        this.pageState.callModes = boot.callModes;
        if (boot.defaultCallModeId != null) this.pageState.selectedCallModeId = boot.defaultCallModeId;
        this.pageState.voicemailStatus = boot.voicemailStatus;
        this.pageState.ringtones = boot.ringtones;

        this.getStatus();
        this.getHistory();
        this.getVoicemails();
        this.getRecordings();
        this.getContacts();
        this.getDiscovery();

        this.controller.bindListeners();

        if (routeQuery?.destination_hash) this.pageState.destinationHash = routeQuery.destination_hash;
        else if (routeQuery?.destinationHash) this.pageState.destinationHash = routeQuery.destinationHash;
        if (routeQuery?.tab) this.onTabChange(routeQuery.tab);
        else GlobalState.activeCallTab = this.pageState.activeTab;
    }

    public destroy(): void {
        this.controller.unbindListeners();
        if (this.endedTimeoutId) clearTimeout(this.endedTimeoutId);
        if (this.searchDebounceId) clearTimeout(this.searchDebounceId);
    }
}

export function createCallPageRuntime(getIsPopout: () => boolean, initialCustomState?: CallPageState): CallPageRuntime {
    return new CallPageRuntime(getIsPopout, initialCustomState);
}
