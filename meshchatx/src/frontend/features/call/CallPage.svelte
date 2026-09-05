<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onDestroy, onMount } from "svelte";
    import GlobalEmitter from "../../js/GlobalEmitter.js";
    import GlobalState from "../../js/GlobalState.js";
    import Utils from "../../js/Utils.js";
    import {
        answerIncomingCall,
        hangupActiveCall,
        placeOutgoingCall,
        sendActiveCallToVoicemail,
        setPttActive,
        switchAudioProfile,
        switchCallMode,
        toggleMicrophone,
        toggleSpeaker,
        updateTelephoneConfig,
        type MutableCallState,
    } from "./lib/callPageActions.js";
    import {
        applyTelephoneStatus,
        clearHistory,
        createCallPageDataState,
        loadAudioProfiles,
        loadCallModes,
        loadConfig,
        loadContacts,
        loadDiscovery,
        loadHistory,
        loadRecordings,
        loadRingtones,
        loadRingtoneStatus,
        loadVoicemails,
        loadVoicemailStatus,
        markMissedCallsViewed,
        type CallPageDataState,
    } from "./lib/callPageData.js";
    import {
        formatBitrate,
        formatBytes,
        formatDateTime,
        formatDestinationHash,
        formatDuration,
        formatNumber,
    } from "./lib/callFormat.js";
    import { CallStatusPoller } from "./lib/callStatusPoll.js";
    import { CallWebAudioBridge } from "./lib/callWebAudio.js";
    import { resolveContactByHash } from "./lib/callHistory.js";
    import CallTabBar from "./components/CallTabBar.svelte";
    import CallPhoneTab from "./components/CallPhoneTab.svelte";
    import CallPhonebookTab from "./components/CallPhonebookTab.svelte";
    import CallVoicemailTab from "./components/CallVoicemailTab.svelte";
    import CallContactsTab from "./components/CallContactsTab.svelte";
    import CallRecordingsTab from "./components/CallRecordingsTab.svelte";
    import CallRingtoneTab from "./components/CallRingtoneTab.svelte";

    interface Props {
        routeQuery?: Record<string, string>;
    }

    let { routeQuery = {} }: Props = $props();

    let data = $state(createCallPageDataState()) as CallPageDataState;
    let activeTab = $state("phone");
    let destinationHash = $state("");
    let callMinimized = $state(false);
    let elapsedTick = $state(0);
    let webAudioBridgeEnabled = $derived(Boolean(data.config?.telephone_web_audio_enabled));
    let showWebAudioDeviceSelector = $derived(webAudioBridgeEnabled && !webAudioBridge.isAndroid());
    let isHalfDuplexCall = $derived(Boolean(data.activeCall?.is_half_duplex));
    let isRingtoneEditorOpen = $state(false);
    let editingRingtoneForAudio = $state<Record<string, unknown> | null>(null);
    let playingVoicemailId = $state<string | number | null>(null);
    let playingRecordingId = $state<string | number | null>(null);
    let playingSide = $state<"rx" | "tx" | null>(null);
    let isGeneratingGreeting = $state(false);
    let isUploadingGreeting = $state(false);
    let isPlayingGreeting = $state(false);
    let isUploadingRingtone = $state(false);
    let isPlayingRingtone = $state(false);
    let audioPlayer: HTMLAudioElement | null = null;

    const webAudioBridge = new CallWebAudioBridge({
        callbacks: {
            onConfigDisable: async () => {
                await updateTelephoneConfig(asMutableState(), { telephone_web_audio_enabled: false });
            },
        },
    });

    let poller: CallStatusPoller | null = null;
    let liveTransportUnsub: (() => void) | null = null;

    const elapsedTime = $derived.by(() => {
        void elapsedTick;
        const call = data.activeCall;
        if (!call?.started_at && !call?.created_at) return "";
        const start = Number(call.started_at || call.created_at || 0);
        if (!start) return "";
        const seconds = Math.max(0, Math.floor(Date.now() / 1000 - start));
        return formatDuration(seconds);
    });

    function asMutableState(): MutableCallState & CallPageDataState {
        return {
            ...data,
            destinationHash,
            activeTab,
            webAudioBridgeEnabled,
            webAudioBridgeRequired: data.webAudioBridgeRequired,
            wasDeclined: data.wasDeclined,
            isCallEnded: data.isCallEnded,
            initiationStatus: data.initiationStatus,
            initiationTargetHash: data.initiationTargetHash,
            initiationTargetName: data.initiationTargetName,
            contacts: data.contacts,
            config: data.config,
            activeCall: data.activeCall,
            localMicMuted: data.localMicMuted,
            localSpeakerMuted: data.localSpeakerMuted,
            localPttActive: data.localPttActive,
            isMicMuting: data.isMicMuting,
            isSpeakerMuting: data.isSpeakerMuting ?? false,
            pttKeyHeld: data.pttKeyHeld,
            selectedCallModeId: data.selectedCallModeId,
            selectedAudioProfileId: data.selectedAudioProfileId,
        };
    }

    function syncFromMutable(state: MutableCallState): void {
        data.activeCall = state.activeCall;
        data.localMicMuted = state.localMicMuted;
        data.localSpeakerMuted = state.localSpeakerMuted;
        data.localPttActive = state.localPttActive;
        data.isMicMuting = state.isMicMuting;
        data.pttKeyHeld = state.pttKeyHeld;
        data.selectedCallModeId = state.selectedCallModeId;
        data.selectedAudioProfileId = state.selectedAudioProfileId;
        data.config = state.config;
        data.initiationStatus = state.initiationStatus;
        data.initiationTargetHash = state.initiationTargetHash;
        data.initiationTargetName = state.initiationTargetName;
        data.isCallEnded = state.isCallEnded;
        data.wasDeclined = state.wasDeclined;
        data.webAudioBridgeRequired = state.webAudioBridgeRequired;
        destinationHash = state.destinationHash;
        activeTab = state.activeTab;
    }

    async function ensureWebAudio(webAudioStatus: {
        enabled?: boolean;
        required?: boolean;
        frame_ms?: number;
    }): Promise<void> {
        if (typeof webAudioStatus.required === "boolean") {
            data.webAudioBridgeRequired = webAudioStatus.required;
        }
        if (!webAudioStatus?.enabled) {
            webAudioBridge.stop();
            return;
        }
        if (data.activeCall?.is_voicemail) {
            webAudioBridge.stop();
            return;
        }
        if (data.activeCall && webAudioStatus.enabled) {
            if (webAudioStatus.frame_ms) {
                webAudioBridge.audioFrameMs = webAudioStatus.frame_ms;
            }
            await webAudioBridge.start();
        } else {
            webAudioBridge.stop();
        }
    }

    async function refreshStatus(): Promise<void> {
        await applyTelephoneStatus(data, {
            ensureWebAudio,
            isPopout: Boolean(routeQuery && (routeQuery as { isPopout?: string }).isPopout),
        });
        await loadVoicemailStatus(data);
        await loadRingtoneStatus(data);
    }

    async function refreshSecondary(): Promise<void> {
        await loadHistory(data);
        await loadVoicemails(data);
        await loadRecordings(data);
        await loadContacts(data);
        await loadDiscovery(data);
    }

    function onWebsocketReconnected(): void {
        void refreshStatus();
        void loadHistory(data);
        void loadVoicemails(data);
        void loadVoicemailStatus(data);
    }

    function onHistoryUpdated(): void {
        void loadHistory(data);
        void loadVoicemails(data);
        void markMissedCallsViewed();
    }

    function isEditableEventTarget(target: EventTarget | null): boolean {
        if (!target || !(target instanceof Element)) return false;
        const tag = (target.tagName || "").toLowerCase();
        if (tag === "input" || tag === "textarea" || tag === "select") return true;
        return Boolean((target as HTMLElement).isContentEditable);
    }

    function onPttKeyDown(event: KeyboardEvent): void {
        if (event.code !== "Space" && event.key !== " ") return;
        if (event.repeat) return;
        if (isEditableEventTarget(event.target)) return;
        if (!isHalfDuplexCall) return;
        event.preventDefault();
        data.pttKeyHeld = true;
        void handleSetPtt(true);
    }

    function onPttKeyUp(event: KeyboardEvent): void {
        if (event.code !== "Space" && event.key !== " ") return;
        if (!data.pttKeyHeld && !data.localPttActive) return;
        event.preventDefault();
        data.pttKeyHeld = false;
        void handleSetPtt(false);
    }

    function onPttWindowBlur(): void {
        data.pttKeyHeld = false;
        if (data.localPttActive) {
            void handleSetPtt(false);
        }
    }

    async function handleCall(hash: string): Promise<void> {
        const state = asMutableState();
        await placeOutgoingCall(state, hash, {
            requestAudioPermission: () => webAudioBridge.requestPermission(),
        });
        syncFromMutable(state);
    }

    async function handleAnswer(): Promise<void> {
        const state = asMutableState();
        await answerIncomingCall(state, {
            requestAudioPermission: () => webAudioBridge.requestPermission(),
        });
        syncFromMutable(state);
    }

    async function handleHangup(): Promise<void> {
        const state = asMutableState();
        await hangupActiveCall(state);
        syncFromMutable(state);
    }

    async function handleToggleMic(): Promise<void> {
        const state = asMutableState();
        await toggleMicrophone(state);
        syncFromMutable(state);
    }

    async function handleToggleSpeaker(): Promise<void> {
        const state = asMutableState();
        await toggleSpeaker(state);
        syncFromMutable(state);
    }

    async function handleSetPtt(active: boolean): Promise<void> {
        const state = asMutableState();
        await setPttActive(state, active);
        syncFromMutable(state);
    }

    async function handleSwitchMode(id: number | string): Promise<void> {
        const state = asMutableState();
        await switchCallMode(state, id);
        syncFromMutable(state);
    }

    async function handleSwitchProfile(id: number | string): Promise<void> {
        const state = asMutableState();
        await switchAudioProfile(state, id);
        syncFromMutable(state);
    }

    async function handleUpdateConfig(patch: Record<string, unknown>): Promise<void> {
        const state = asMutableState();
        await updateTelephoneConfig(state, patch);
        syncFromMutable(state);
    }

    async function handleToggleWebAudio(enabled: boolean): Promise<void> {
        if (!data.config) return;
        if (data.webAudioBridgeRequired && !enabled) return;
        const previous = data.config.telephone_web_audio_enabled;
        data.config.telephone_web_audio_enabled = enabled;
        try {
            if (enabled) {
                const permitted = await webAudioBridge.requestPermission();
                if (!permitted) {
                    data.config.telephone_web_audio_enabled = false;
                    await handleUpdateConfig({ telephone_web_audio_enabled: false });
                    return;
                }
            }
            await handleUpdateConfig({ telephone_web_audio_enabled: enabled });
            if (enabled && data.activeCall) {
                await webAudioBridge.start();
            } else if (!enabled) {
                webAudioBridge.stop();
            }
        } catch {
            data.config.telephone_web_audio_enabled = previous;
        }
    }

    function setActiveTab(tab: string): void {
        activeTab = tab;
        GlobalState.activeCallTab = tab;
        if (tab === "recordings") {
            void loadRecordings(data);
        }
    }

    function getContactByHash(hash: string) {
        return resolveContactByHash(hash, data.contacts) || undefined;
    }

    function copyHash(hash: string): void {
        if (typeof navigator !== "undefined" && navigator.clipboard) {
            void navigator.clipboard.writeText(hash);
        }
    }

    onMount(() => {
        if (routeQuery.destination_hash) {
            destinationHash = routeQuery.destination_hash;
        }
        if (routeQuery.tab) {
            activeTab = routeQuery.tab;
            GlobalState.activeCallTab = routeQuery.tab;
        }

        void loadConfig(data);
        void loadAudioProfiles(data);
        void loadCallModes(data);
        void refreshStatus();
        void refreshSecondary();
        void loadVoicemailStatus(data);
        void loadRingtones(data);
        void loadRingtoneStatus(data);
        void markMissedCallsViewed();

        GlobalEmitter.on("telephone-history-updated", onHistoryUpdated);
        GlobalEmitter.on("websocket-reconnected", onWebsocketReconnected);

        poller = new CallStatusPoller({
            onPollStatus: () => refreshStatus(),
            onPollHistory: () => refreshSecondary(),
            onElapsedTick: () => {
                elapsedTick += 1;
            },
            isLiveTransportReady: () => Boolean(GlobalState.liveTransportReady),
        });
        poller.startStatusPoll();
        poller.startHistoryPoll();
        poller.startElapsedTick();

        liveTransportUnsub = GlobalState.$watch
            ? GlobalState.$watch("liveTransportReady", () => poller?.startStatusPoll())
            : null;
        // Fallback poll restart when live transport flips
        const liveWatchId = setInterval(() => {
            poller?.startStatusPoll();
        }, 30000);
        onDestroy(() => clearInterval(liveWatchId));

        window.addEventListener("keydown", onPttKeyDown);
        window.addEventListener("keyup", onPttKeyUp);
        window.addEventListener("blur", onPttWindowBlur);
    });

    onDestroy(() => {
        GlobalEmitter.off("telephone-history-updated", onHistoryUpdated);
        GlobalEmitter.off("websocket-reconnected", onWebsocketReconnected);
        liveTransportUnsub?.();
        poller?.stopAll();
        window.removeEventListener("keydown", onPttKeyDown);
        window.removeEventListener("keyup", onPttKeyUp);
        window.removeEventListener("blur", onPttWindowBlur);
        if (data.localPttActive) {
            void handleSetPtt(false);
        }
        if (audioPlayer) {
            audioPlayer.pause();
            audioPlayer = null;
        }
        webAudioBridge.stop();
        if (data.endedTimeout) clearTimeout(data.endedTimeout);
    });
</script>

<div class="flex min-w-0 h-full flex-1 flex-col">
    <div class="flex h-full w-full flex-col bg-gray-100 dark:bg-zinc-950">
        <div class="w-full h-full overflow-y-auto">
            <div class="mx-auto w-full max-w-4xl p-4 md:p-6 flex-1 flex flex-col min-h-full">
                <CallTabBar
                    {activeTab}
                    unreadVoicemailsCount={data.unreadVoicemailsCount}
                    ontabchange={setActiveTab}
                />

                {#if activeTab === "phone"}
                    <CallPhoneTab
                        config={data.config}
                        activeCall={data.activeCall}
                        lastCall={data.lastCall}
                        isCallEnded={data.isCallEnded}
                        wasDeclined={data.wasDeclined}
                        wasVoicemail={data.wasVoicemail}
                        {elapsedTime}
                        initiationStatus={data.initiationStatus}
                        initiationTargetName={data.initiationTargetName || ""}
                        initiationTargetHash={data.initiationTargetHash || ""}
                        {callMinimized}
                        {destinationHash}
                        audioProfiles={data.audioProfiles}
                        callModes={data.callModes}
                        selectedAudioProfileId={data.selectedAudioProfileId || ""}
                        selectedCallModeId={data.selectedCallModeId || ""}
                        isMicMuted={data.localMicMuted}
                        isSpeakerMuted={data.localSpeakerMuted}
                        localPttActive={data.localPttActive}
                        {isHalfDuplexCall}
                        {playingVoicemailId}
                        contacts={data.contacts}
                        callHistory={data.callHistory}
                        hasMoreCallHistory={data.hasMoreCallHistory}
                        callHistorySearch={data.callHistorySearch}
                        {webAudioBridgeEnabled}
                        webAudioBridgeRequired={data.webAudioBridgeRequired}
                        {showWebAudioDeviceSelector}
                        selectedAudioInputId={webAudioBridge.selectedAudioInputId}
                        selectedAudioOutputId={webAudioBridge.selectedAudioOutputId}
                        audioInputDevices={webAudioBridge.audioInputDevices}
                        audioOutputDevices={webAudioBridge.audioOutputDevices}
                        isAndroid={webAudioBridge.isAndroid()}
                        {getContactByHash}
                        {formatDestinationHash}
                        {formatDateTime}
                        {formatDuration}
                        {formatNumber}
                        {formatBytes}
                        {formatBitrate}
                        onupdateconfig={handleUpdateConfig}
                        ondestinationchange={(v) => (destinationHash = v)}
                        oncall={handleCall}
                        onhangup={handleHangup}
                        onanswer={handleAnswer}
                        onsendtovoicemail={() => void sendActiveCallToVoicemail()}
                        onexpandcall={() => (callMinimized = false)}
                        onminimizecall={() => (callMinimized = true)}
                        ontogglemic={handleToggleMic}
                        ontogglespeaker={handleToggleSpeaker}
                        onsetptt={handleSetPtt}
                        onselectaudioprofile={handleSwitchProfile}
                        onselectcallmode={handleSwitchMode}
                        onchangeaudioprofile={handleSwitchProfile}
                        onchangecallmode={handleSwitchMode}
                        ontogglednd={(val) => void handleUpdateConfig({ telephone_do_not_disturb: val })}
                        ontogglecontactsonly={(val) =>
                            void handleUpdateConfig({ telephone_allow_calls_from_contacts_only: val })}
                        ontoggletelephoneannounce={(val) =>
                            void handleUpdateConfig({ telephone_announce_enabled: val })}
                        ontogglewebaudio={handleToggleWebAudio}
                        onrefreshaudiodevices={() => void webAudioBridge.refreshDevices()}
                        onrestartwebaudio={() => void webAudioBridge.restart()}
                        onselectaudioinput={(id) => {
                            webAudioBridge.selectedAudioInputId = id;
                        }}
                        onselectaudiooutput={(id) => {
                            webAudioBridge.selectedAudioOutputId = id;
                        }}
                        onclearhistory={() => void clearHistory(data)}
                        onhistorysearch={(q) => {
                            data.callHistorySearch = q;
                            void loadHistory(data);
                        }}
                        oncallback={(hash) => void handleCall(hash)}
                        onloadmorehistory={() => {
                            data.callHistoryOffset += data.callHistoryLimit;
                            void loadHistory(data, true);
                        }}
                        oncopyhash={copyHash}
                        onblockidentity={(hash) => {
                            void import("./lib/callApi.js").then((api) => api.blockDestination?.(hash));
                        }}
                    />
                {/if}

                <CallPhonebookTab
                    active={activeTab === "phonebook"}
                    discoveryAnnounces={data.discoveryAnnounces}
                    discoverySearch={data.discoverySearch}
                    hasMoreDiscovery={data.hasMoreDiscovery}
                    {formatDestinationHash}
                    onsearchinput={(q) => {
                        data.discoverySearch = q;
                        void loadDiscovery(data);
                    }}
                    oncall={(hash) => void handleCall(hash)}
                    onloadmore={() => {
                        data.discoveryOffset += data.discoveryLimit;
                        void loadDiscovery(data, true);
                    }}
                    oncopyhash={copyHash}
                />

                <CallVoicemailTab
                    active={activeTab === "voicemail"}
                    config={data.config}
                    voicemailStatus={data.voicemailStatus}
                    voicemails={data.voicemails}
                    {isGeneratingGreeting}
                    {isUploadingGreeting}
                    {isPlayingGreeting}
                    {getContactByHash}
                    {formatDateTime}
                    {formatDuration}
                    {formatDestinationHash}
                    onupdateconfig={handleUpdateConfig}
                    oncopyhash={copyHash}
                    oncallback={(hash) => void handleCall(hash)}
                />

                <CallContactsTab
                    active={activeTab === "contacts"}
                    contactsSearch={data.contactsSearch}
                    contacts={data.contacts}
                    {formatDestinationHash}
                    onsearchinput={(q) => {
                        data.contactsSearch = q;
                        void loadContacts(data);
                    }}
                    oncall={(hash) => void handleCall(hash)}
                    oncopyhash={copyHash}
                />

                {#if activeTab === "ringtone"}
                    <CallRingtoneTab
                        config={data.config}
                        ringtones={data.ringtones}
                        ringtoneStatus={data.ringtoneStatus}
                        {isRingtoneEditorOpen}
                        {editingRingtoneForAudio}
                        {isUploadingRingtone}
                        {isPlayingRingtone}
                        onupdateconfig={handleUpdateConfig}
                        onopeneditor={(ringtone) => {
                            editingRingtoneForAudio = ringtone;
                            isRingtoneEditorOpen = true;
                        }}
                        oncloseeditor={() => {
                            isRingtoneEditorOpen = false;
                            editingRingtoneForAudio = null;
                        }}
                        onringtonesaved={() => {
                            isRingtoneEditorOpen = false;
                            void loadRingtones(data);
                            void loadRingtoneStatus(data);
                        }}
                    />
                {/if}

                {#if activeTab === "recordings"}
                    <CallRecordingsTab
                        recordings={data.recordings}
                        recordingSearch={data.recordingSearch}
                        {playingRecordingId}
                        {playingSide}
                        {formatDestinationHash}
                        {formatDateTime}
                        {formatDuration}
                        onsearchinput={(q) => {
                            data.recordingSearch = q;
                            void loadRecordings(data);
                        }}
                        oncopyhash={copyHash}
                    />
                {/if}
            </div>
        </div>
    </div>
</div>
