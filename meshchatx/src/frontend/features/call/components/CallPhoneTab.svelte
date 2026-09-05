<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import LxmfUserIcon from "../../../ui/svelte/LxmfUserIcon.svelte";
    import {
        formatDestinationHash as defaultFormatHash,
        formatDateTime as defaultFormatDt,
        formatDuration as defaultFormatDur,
        formatNumber as defaultFormatNum,
        formatBytes as defaultFormatB,
        formatBitrate as defaultFormatBr,
    } from "../lib/callFormat.js";
    import { t } from "../../../js/i18n.js";
    import CallActiveSession from "./CallActiveSession.svelte";
    import CallAudioSettings from "./CallAudioSettings.svelte";
    import CallHistoryPanel from "./CallHistoryPanel.svelte";

    interface AudioDevice {
        deviceId: string;
        label?: string;
    }

    interface Props {
        config?: Record<string, any> | null;
        activeCall?: Record<string, any> | null;
        lastCall?: Record<string, any> | null;
        isCallEnded?: boolean;
        wasDeclined?: boolean;
        wasVoicemail?: boolean;
        callDuration?: string;
        elapsedTime?: string;
        initiationStatus?: string | null;
        initiationTargetName?: string;
        initiationTargetHash?: string;
        callMinimized?: boolean;
        destinationHash?: string;
        audioProfiles?: Array<{ id: number | string; name: string }>;
        callModes?: Array<{ id: number | string; name: string }>;
        selectedAudioProfileId?: number | string;
        selectedCallModeId?: number | string;
        isMicMuted?: boolean;
        isSpeakerMuted?: boolean;
        localPttActive?: boolean;
        isHalfDuplexCall?: boolean;
        playingVoicemailId?: string | number | null;
        contacts?: Array<any>;
        callHistory?: Array<any>;
        hasMoreCallHistory?: boolean;
        callHistorySearch?: string;
        webAudioBridgeEnabled?: boolean;
        webAudioBridgeRequired?: boolean;
        showWebAudioDeviceSelector?: boolean;
        selectedAudioInputId?: string;
        selectedAudioOutputId?: string;
        audioInputDevices?: AudioDevice[];
        audioOutputDevices?: AudioDevice[];
        isAndroid?: boolean;
        getContactByHash?: (hash: string) => { custom_image?: string } | null | undefined;
        formatDestinationHash?: (hash?: string) => string;
        formatDateTime?: (ms: number) => string;
        formatDuration?: (seconds: number) => string;
        formatNumber?: (value?: number | null) => string;
        formatBytes?: (bytes?: number | null) => string;
        formatBitrate?: (bps?: number | null) => string;
        onupdateconfig?: (patch: Record<string, unknown>) => void;
        oncall?: (hash: string) => void;
        onhangup?: () => void;
        onanswer?: () => void;
        onsendtovoicemail?: () => void;
        onexpandcall?: () => void;
        onminimizecall?: () => void;
        ontogglemic?: () => void;
        ontogglespeaker?: () => void;
        onsetptt?: (active: boolean) => void;
        onselectaudioprofile?: (id: number | string) => void;
        onselectcallmode?: (id: number | string) => void;
        onplaylatestvoicemail?: () => void;
        ontogglednd?: (val: boolean) => void;
        ontogglecontactsonly?: (val: boolean) => void;
        ontoggletelephoneannounce?: (val: boolean) => void;
        ontogglewebaudio?: (val: boolean) => void;
        onchangeaudioprofile?: (profileId: number | string) => void;
        onchangecallmode?: (modeId: number | string) => void;
        onrefreshaudiodevices?: () => void;
        onrestartwebaudio?: () => void;
        onselectaudioinput?: (id: string) => void;
        onselectaudiooutput?: (id: string) => void;
        onclearhistory?: () => void;
        onhistorysearch?: (query: string) => void;
        onaddcontactfromhistory?: (entry: any) => void;
        onblockidentity?: (hash: string) => void;
        onopenmessagefromhistory?: (entry: any) => void;
        oncallback?: (hash: string) => void;
        onloadmorehistory?: () => void;
        oncopyhash?: (hash: string) => void;
    }

    let {
        config = null,
        activeCall = null,
        lastCall = null,
        isCallEnded = false,
        wasDeclined = false,
        wasVoicemail = false,
        callDuration = "",
        elapsedTime = "",
        initiationStatus = null,
        initiationTargetName = "",
        initiationTargetHash = "",
        callMinimized = false,
        destinationHash = $bindable(""),
        audioProfiles = [],
        callModes = [],
        selectedAudioProfileId = "",
        selectedCallModeId = "",
        isMicMuted = false,
        isSpeakerMuted = false,
        localPttActive = false,
        isHalfDuplexCall = false,
        playingVoicemailId = null,
        contacts = [],
        callHistory = [],
        hasMoreCallHistory = false,
        callHistorySearch = "",
        webAudioBridgeEnabled = false,
        webAudioBridgeRequired = false,
        showWebAudioDeviceSelector = false,
        selectedAudioInputId = "",
        selectedAudioOutputId = "",
        audioInputDevices = [],
        audioOutputDevices = [],
        isAndroid = false,
        getContactByHash,
        formatDestinationHash = defaultFormatHash,
        formatDateTime = defaultFormatDt,
        formatDuration = defaultFormatDur,
        formatNumber = defaultFormatNum,
        formatBytes = defaultFormatB,
        formatBitrate = defaultFormatBr,
        onupdateconfig,
        oncall,
        onhangup,
        onanswer,
        onsendtovoicemail,
        onexpandcall,
        onminimizecall,
        ontogglemic,
        ontogglespeaker,
        onsetptt,
        onselectaudioprofile,
        onselectcallmode,
        onplaylatestvoicemail,
        ontogglednd,
        ontogglecontactsonly,
        ontoggletelephoneannounce,
        ontogglewebaudio,
        onchangeaudioprofile,
        onchangecallmode,
        onrefreshaudiodevices,
        onrestartwebaudio,
        onselectaudioinput,
        onselectaudiooutput,
        onclearhistory,
        onhistorysearch,
        onaddcontactfromhistory,
        onblockidentity,
        onopenmessagefromhistory,
        oncallback,
        onloadmorehistory,
        oncopyhash,
    }: Props = $props();

    let isCallInputFocused = $state(false);
    let selectedSuggestionIndex = $state(-1);

    const isFullCallSessionActive = $derived(
        Boolean((activeCall || isCallEnded || initiationStatus) && !callMinimized)
    );

    const newCallSuggestions = $derived.by(() => {
        if (!isCallInputFocused) return [];
        const search = (destinationHash || "").toLowerCase().trim();
        const suggestions: Array<{
            name: string;
            hash: string;
            type: "contact" | "history";
            icon: string;
        }> = [];
        const seenHashes = new Set<string>();

        for (const c of contacts) {
            const rawId = c.remote_identity_hash;
            if (!rawId || seenHashes.has(rawId)) continue;
            const hash = (c.remote_telephony_hash || c.remote_destination_hash || rawId).toLowerCase();
            const name = c.name || "";
            if (!search || name.toLowerCase().includes(search) || rawId.toLowerCase().includes(search) || hash.includes(search)) {
                suggestions.push({
                    name,
                    hash: c.remote_telephony_hash || c.remote_destination_hash || rawId,
                    type: "contact",
                    icon: "account",
                });
                seenHashes.add(rawId);
            }
        }

        for (const h of callHistory) {
            const rawId = h.remote_identity_hash;
            if (!rawId || seenHashes.has(rawId)) continue;
            const name = h.remote_identity_name || (typeof rawId === "string" ? rawId.substring(0, 8) : "");
            if (
                !search ||
                (h.remote_identity_name && h.remote_identity_name.toLowerCase().includes(search)) ||
                (typeof rawId === "string" && rawId.toLowerCase().includes(search))
            ) {
                suggestions.push({
                    name,
                    hash: h.remote_telephony_hash || h.remote_destination_hash || rawId,
                    type: "history",
                    icon: "history",
                });
                seenHashes.add(rawId);
            }
        }

        return suggestions.slice(0, 8);
    });

    function handleCallInputUp() {
        if (newCallSuggestions.length > 0) {
            if (selectedSuggestionIndex > 0) {
                selectedSuggestionIndex--;
            } else {
                selectedSuggestionIndex = newCallSuggestions.length - 1;
            }
        }
    }

    function handleCallInputDown() {
        if (newCallSuggestions.length > 0) {
            if (selectedSuggestionIndex < newCallSuggestions.length - 1) {
                selectedSuggestionIndex++;
            } else {
                selectedSuggestionIndex = 0;
            }
        }
    }

    function handleCallInputEnter() {
        if (selectedSuggestionIndex >= 0 && selectedSuggestionIndex < newCallSuggestions.length) {
            const suggestion = newCallSuggestions[selectedSuggestionIndex];
            selectSuggestion(suggestion);
        } else {
            oncall?.(destinationHash);
        }
    }

    function selectSuggestion(suggestion: { hash: string }) {
        destinationHash = suggestion.hash;
        isCallInputFocused = false;
        selectedSuggestionIndex = -1;
        oncall?.(destinationHash);
    }

    function onCallInputBlur() {
        setTimeout(() => {
            isCallInputFocused = false;
            selectedSuggestionIndex = -1;
        }, 200);
    }
</script>

<div class="flex-1 flex flex-col pt-2">
    {#if config && !config.telephone_enabled}
        <div class="flex-1 flex flex-col items-center justify-center py-12 px-4">
            <div
                class="w-full max-w-md bg-sem-surface border border-sem-border rounded-2xl p-8 flex flex-col items-center text-center shadow-xl"
            >
                <div
                    class="size-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mb-4"
                >
                    <MaterialDesignIcon iconName="phone-off" class="size-8 text-red-600 dark:text-red-400" />
                </div>
                <h2 class="text-xl font-bold text-sem-fg mb-2">{t("call.lxst_disabled_title")}</h2>
                <p class="text-sm text-sem-fg-muted mb-6">{t("call.lxst_disabled_body")}</p>
                <button
                    type="button"
                    class="primary-chip rounded-2xl! py-3! px-6! text-sm! focus-ring-sem"
                    onclick={() => onupdateconfig?.({ telephone_enabled: true })}
                >
                    <MaterialDesignIcon iconName="phone" class="size-5" />
                    {t("call.enable_lxst")}
                </button>
            </div>
        </div>
    {/if}

    {#if config?.telephone_enabled}
        {#if callMinimized && activeCall}
            <div class="w-full shrink-0 border-b border-sem-border">
                <div
                    class="flex items-center gap-3 px-4 py-2 bg-blue-50/80 dark:bg-blue-900/20 backdrop-blur-sm"
                >
                    <div class="relative">
                        <div
                            class="size-8 rounded-full bg-sem-surface-muted flex items-center justify-center overflow-hidden"
                        >
                            <LxmfUserIcon
                                customImage={activeCall?.custom_image}
                                iconName={activeCall?.remote_icon?.icon_name || "account"}
                                iconForegroundColour={activeCall?.remote_icon?.foreground_colour}
                                iconBackgroundColour={activeCall?.remote_icon?.background_colour}
                                iconClass="size-7"
                            />
                        </div>
                        <div
                            class="absolute -bottom-0.5 -right-0.5 size-2.5 bg-green-500 rounded-full border-2 border-white dark:border-zinc-900"
                        ></div>
                    </div>
                    <div class="flex-1 min-w-0">
                        <div class="text-sm font-bold text-sem-fg truncate">
                            {activeCall?.remote_identity_name || t("call.unknown")}
                        </div>
                        <div class="text-[10px] text-sem-fg-muted flex items-center gap-2">
                            <span class="size-1.5 bg-green-500 rounded-full animate-pulse"></span>
                            <span>{t("call.active")}</span>
                            {#if elapsedTime}
                                <span class="font-mono">· {elapsedTime}</span>
                            {/if}
                        </div>
                    </div>
                    <div class="flex items-center gap-1 shrink-0">
                        <button
                            type="button"
                            class="size-8 flex items-center justify-center rounded-full hover:bg-black/5 dark:hover:bg-white/10 transition-colors text-sem-fg-muted"
                            title="Expand call"
                            onclick={() => onexpandcall?.()}
                        >
                            <MaterialDesignIcon iconName="chevron-up" class="size-5" />
                        </button>
                        <button
                            type="button"
                            class="size-8 flex items-center justify-center rounded-full hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors text-red-600 dark:text-red-400"
                            title="Hangup"
                            onclick={() => onhangup?.()}
                        >
                            <MaterialDesignIcon iconName="phone-hangup" class="size-4 rotate-135" />
                        </button>
                    </div>
                </div>
            </div>
        {/if}

        {#if isFullCallSessionActive}
            <CallActiveSession
                {activeCall}
                {lastCall}
                {isCallEnded}
                {wasDeclined}
                {wasVoicemail}
                {callDuration}
                {elapsedTime}
                {initiationStatus}
                {initiationTargetName}
                {initiationTargetHash}
                {audioProfiles}
                {callModes}
                {selectedAudioProfileId}
                {selectedCallModeId}
                {isMicMuted}
                {isSpeakerMuted}
                {localPttActive}
                {isHalfDuplexCall}
                {playingVoicemailId}
                {formatDestinationHash}
                {formatNumber}
                {formatBytes}
                {formatBitrate}
                {onplaylatestvoicemail}
                {onselectaudioprofile}
                {onselectcallmode}
                {ontogglemic}
                {ontogglespeaker}
                {onsetptt}
                {onanswer}
                {onsendtovoicemail}
                onminimize={onminimizecall}
                {onhangup}
            />
        {:else}
            <div class="space-y-6 my-6 max-w-3xl mx-auto w-full">
                <div class="w-full border-b border-sem-border py-2">
                    <div class="flex items-center gap-3 mb-6">
                        <div class="bg-blue-100 dark:bg-blue-900/30 p-2.5 rounded-2xl">
                            <MaterialDesignIcon iconName="phone-plus" class="size-6 text-sem-accent" />
                        </div>
                        <div>
                            <h2 class="text-lg font-bold text-sem-fg leading-tight">New Call</h2>
                            <p class="text-xs text-sem-fg-muted">Enter an identity to call.</p>
                        </div>
                    </div>

                    <div class="space-y-4">
                        <div class="relative">
                            <div class="flex gap-2">
                                <div class="relative flex-1">
                                    <input
                                        bind:value={destinationHash}
                                        type="text"
                                        placeholder={t("call.identity_or_name")}
                                        class="input-field"
                                        onkeydown={(e) => {
                                            if (e.key === "Enter") {
                                                e.preventDefault();
                                                handleCallInputEnter();
                                            } else if (e.key === "ArrowUp") {
                                                e.preventDefault();
                                                handleCallInputUp();
                                            } else if (e.key === "ArrowDown") {
                                                e.preventDefault();
                                                handleCallInputDown();
                                            }
                                        }}
                                        onfocus={() => (isCallInputFocused = true)}
                                        onblur={onCallInputBlur}
                                    />
                                    {#if isCallInputFocused && newCallSuggestions.length > 0}
                                        <div
                                            class="absolute z-50 left-0 right-0 mt-1 bg-sem-surface border border-sem-border rounded-xl shadow-xl overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200"
                                        >
                                            {#each newCallSuggestions as suggestion, index (suggestion.hash)}
                                                <div
                                                    class="px-4 py-2.5 flex items-center gap-3 cursor-pointer transition-colors {index ===
                                                    selectedSuggestionIndex
                                                        ? 'bg-blue-50 dark:bg-blue-900/30 text-sem-accent'
                                                        : 'hover:bg-sem-surface-muted/50 text-sem-fg-muted'}"
                                                    role="button"
                                                    tabindex="0"
                                                    onkeydown={(e) => {
                                                        if (e.key === "Enter" || e.key === " ") {
                                                            e.preventDefault();
                                                            selectSuggestion(suggestion);
                                                        }
                                                    }}
                                                    onmousedown={(e) => {
                                                        e.preventDefault();
                                                        selectSuggestion(suggestion);
                                                    }}
                                                >
                                                    <div
                                                        class="shrink-0 size-8 rounded-full flex items-center justify-center text-xs {suggestion.type ===
                                                        'contact'
                                                            ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-600'
                                                            : 'bg-sem-surface-muted text-gray-500'}"
                                                    >
                                                        <MaterialDesignIcon
                                                            iconName={suggestion.icon}
                                                            class="size-4"
                                                        />
                                                    </div>
                                                    <div class="flex-1 min-w-0">
                                                        <div class="text-sm font-bold truncate">
                                                            {suggestion.name}
                                                        </div>
                                                        <button
                                                            type="button"
                                                            class="text-[10px] font-mono opacity-50 truncate hover:text-blue-500 transition-colors cursor-pointer text-left block"
                                                            title={suggestion.hash}
                                                            onmousedown={(e) => {
                                                                e.stopPropagation();
                                                                oncopyhash?.(suggestion.hash);
                                                            }}
                                                        >
                                                            {formatDestinationHash(suggestion.hash)}
                                                        </button>
                                                    </div>
                                                    {#if suggestion.type === "contact"}
                                                        <div
                                                            class="text-[10px] uppercase font-bold tracking-widest opacity-30"
                                                        >
                                                            Contact
                                                        </div>
                                                    {/if}
                                                </div>
                                            {/each}
                                        </div>
                                    {/if}
                                </div>
                                <button
                                    type="button"
                                    class="bg-blue-600 hover:bg-blue-500 text-white px-6 rounded-2xl font-bold shadow-lg shadow-blue-500/20 transition-all flex items-center gap-2"
                                    onclick={() => oncall?.(destinationHash)}
                                >
                                    <MaterialDesignIcon iconName="phone" class="size-5" />
                                    Call
                                </button>
                            </div>
                        </div>

                        <CallAudioSettings
                            {config}
                            {webAudioBridgeEnabled}
                            {webAudioBridgeRequired}
                            {showWebAudioDeviceSelector}
                            {selectedAudioInputId}
                            {selectedAudioOutputId}
                            {audioInputDevices}
                            {audioOutputDevices}
                            {audioProfiles}
                            {callModes}
                            {isAndroid}
                            {ontogglednd}
                            {ontogglecontactsonly}
                            {ontoggletelephoneannounce}
                            {ontogglewebaudio}
                            {onchangeaudioprofile}
                            {onchangecallmode}
                            {onselectaudioinput}
                            {onselectaudiooutput}
                            {onrefreshaudiodevices}
                            {onrestartwebaudio}
                        />
                    </div>
                </div>

                {#if callHistory.length > 0}
                    <CallHistoryPanel
                        {callHistory}
                        {hasMoreCallHistory}
                        {callHistorySearch}
                        {getContactByHash}
                        {formatDestinationHash}
                        {formatDateTime}
                        {formatDuration}
                        {onclearhistory}
                        onsearchinput={onhistorysearch}
                        onaddcontact={onaddcontactfromhistory}
                        {onblockidentity}
                        onopenmessage={onopenmessagefromhistory}
                        oncallback={oncallback}
                        onloadmore={onloadmorehistory}
                        {oncopyhash}
                    />
                {/if}
            </div>
        {/if}
    {/if}
</div>
