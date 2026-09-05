// SPDX-License-Identifier: 0BSD

import type { ActiveCall, TelephoneConfig } from "./types.js";

/**
 * Audio profile selectable option
 */
export interface AudioProfileOption {
    id: number | string;
    name: string;
}

/**
 * Call mode selectable option
 */
export interface CallModeOption {
    id: number | string;
    name: string;
}

/**
 * Autocomplete suggestion item for new calls
 */
export interface SuggestionItem {
    hash: string;
    name: string;
    icon?: string;
    type?: string;
}

/**
 * Props for CallActiveSession component
 */
export interface CallActiveSessionProps {
    activeCall?: Partial<ActiveCall> | null;
    lastCall?: Partial<ActiveCall> | null;
    isCallEnded?: boolean;
    wasDeclined?: boolean;
    wasVoicemail?: boolean;
    callDuration?: string;
    elapsedTime?: string;
    initiationStatus?: string | null;
    initiationTargetName?: string | null;
    initiationTargetHash?: string | null;
    audioProfiles?: AudioProfileOption[];
    callModes?: CallModeOption[];
    selectedAudioProfileId?: number | string;
    selectedCallModeId?: number | string;
    isMicMuted?: boolean;
    isSpeakerMuted?: boolean;
    localPttActive?: boolean;
    isHalfDuplexCall?: boolean;
    playingVoicemailId?: string | number | null;
    formatDestinationHash?: (hash?: string) => string;
    formatNumber?: (value?: number | null) => string;
    formatBytes?: (bytes?: number | null) => string;
    formatBitrate?: (bps?: number | null) => string;
    onplaylatestvoicemail?: () => void;
    onselectaudioprofile?: (id: number | string) => void;
    onselectcallmode?: (id: number | string) => void;
    ontogglemic?: () => void;
    ontogglespeaker?: () => void;
    onsetptt?: (active: boolean) => void;
    onanswer?: () => void;
    onsendtovoicemail?: () => void;
    onminimize?: () => void;
    onhangup?: () => void;
}

/**
 * Props for CallPhoneTab component
 */
export interface CallPhoneTabProps {
    config?: Partial<TelephoneConfig> | null;
    activeCall?: Partial<ActiveCall> | null;
    lastCall?: Partial<ActiveCall> | null;
    isCallEnded?: boolean;
    wasDeclined?: boolean;
    wasVoicemail?: boolean;
    callDuration?: string;
    elapsedTime?: string;
    initiationStatus?: string | null;
    initiationTargetName?: string | null;
    initiationTargetHash?: string | null;
    callMinimized?: boolean;
    destinationHash?: string;
    suggestions?: SuggestionItem[];
    isCallInputFocused?: boolean;
    selectedSuggestionIndex?: number;
    contacts?: any[];
    callHistory?: any[];
    hasMoreCallHistory?: boolean;
    callHistorySearch?: string;
    isLoadingHistory?: boolean;
    audioProfiles?: AudioProfileOption[];
    callModes?: CallModeOption[];
    selectedAudioProfileId?: number | string;
    selectedCallModeId?: number | string;
    isMicMuted?: boolean;
    isSpeakerMuted?: boolean;
    localPttActive?: boolean;
    isHalfDuplexCall?: boolean;
    playingVoicemailId?: string | number | null;
    webAudioBridgeEnabled?: boolean;
    webAudioBridgeRequired?: boolean;
    showWebAudioDeviceSelector?: boolean;
    selectedAudioInputId?: string;
    selectedAudioOutputId?: string;
    audioInputDevices?: any[];
    audioOutputDevices?: any[];
    isAndroid?: boolean;
    getContactByHash?: (hash: string) => any;
    formatDestinationHash?: (hash?: string) => string;
    formatNumber?: (val?: number | null) => string;
    formatBytes?: (bytes?: number | null) => string;
    formatBitrate?: (bps?: number | null) => string;
    formatDateTime?: (ms: number) => string;
    formatDuration?: (sec: number) => string;
    onupdateconfig?: (patch: Partial<TelephoneConfig>) => void;
    oncall?: (hash: string) => void;
    onhangup?: () => void;
    onanswer?: () => void;
    onsendtovoicemail?: () => void;
    ontogglemic?: () => void;
    ontogglespeaker?: () => void;
    onsetptt?: (active: boolean) => void;
    onselectaudioprofile?: (id: number | string) => void;
    onselectcallmode?: (id: number | string) => void;
    onplaylatestvoicemail?: () => void;
    onclearhistory?: () => void;
    onhistorysearch?: (val: string) => void;
    onloadmorehistory?: () => void;
    onaddcontact?: (entry: any) => void;
    onblockidentity?: (hash: string) => void;
    onopenmessage?: (entry: any) => void;
    oncallback?: (hash: string) => void;
    oncopyhash?: (hash: string) => void;
    ontogglednd?: (enabled: boolean) => void;
    ontogglecontactsonly?: (enabled: boolean) => void;
    ontoggletelephoneannounce?: (enabled: boolean) => void;
    ontogglewebaudio?: (enabled: boolean) => void;
    onselectaudioinput?: (id: string) => void;
    onselectaudiooutput?: (id: string) => void;
    onrefreshaudiodevices?: () => void;
    onrestartwebaudio?: () => void;
    onselectsuggestion?: (suggestion: SuggestionItem) => void;
    [key: string]: unknown;
}
