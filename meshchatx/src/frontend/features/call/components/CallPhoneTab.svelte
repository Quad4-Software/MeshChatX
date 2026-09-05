<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import LxmfUserIcon from "../../../ui/svelte/LxmfUserIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import { formatDestinationHash as defaultFormatHash } from "../lib/callFormat.js";
    import CallActiveSession from "./CallActiveSession.svelte";
    import CallAudioSettings from "./CallAudioSettings.svelte";
    import CallHistoryPanel from "./CallHistoryPanel.svelte";
    import type { CallPhoneTabProps, SuggestionItem } from "../lib/callUiTypes.js";

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
        callMinimized = $bindable(false),
        destinationHash = $bindable(""),
        suggestions = [],
        isCallInputFocused = $bindable(false),
        selectedSuggestionIndex = $bindable(0),
        callHistory = [],
        hasMoreCallHistory = false,
        callHistorySearch = "",
        audioProfiles = [],
        callModes = [],
        selectedAudioProfileId = "",
        selectedCallModeId = "",
        isMicMuted = false,
        isSpeakerMuted = false,
        localPttActive = false,
        isHalfDuplexCall = false,
        playingVoicemailId = null,
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
        formatNumber,
        formatBytes,
        formatBitrate,
        formatDateTime,
        formatDuration,
        onupdateconfig,
        oncall,
        onhangup,
        onanswer,
        onsendtovoicemail,
        ontogglemic,
        ontogglespeaker,
        onsetptt,
        onselectaudioprofile,
        onselectcallmode,
        onplaylatestvoicemail,
        onclearhistory,
        onhistorysearch,
        onloadmorehistory,
        onaddcontact,
        onblockidentity,
        onopenmessage,
        oncallback,
        oncopyhash,
        ontogglednd,
        ontogglecontactsonly,
        ontoggletelephoneannounce,
        ontogglewebaudio,
        onselectaudioinput,
        onselectaudiooutput,
        onrefreshaudiodevices,
        onrestartwebaudio,
        onselectsuggestion,
    }: CallPhoneTabProps = $props();

    const isSessionActive = $derived(
        Boolean((activeCall || isCallEnded || initiationStatus) && !callMinimized)
    );

    function handleCallSubmit() {
        if (destinationHash.trim()) {
            oncall?.(destinationHash.trim());
        }
    }

    function handleInputKeydown(e: KeyboardEvent) {
        if (e.key === "Enter") {
            e.preventDefault();
            if (suggestions.length > 0 && selectedSuggestionIndex >= 0 && selectedSuggestionIndex < suggestions.length) {
                const s = suggestions[selectedSuggestionIndex];
                if (s) {
                    onselectsuggestion?.(s);
                    return;
                }
            }
            handleCallSubmit();
        } else if (e.key === "ArrowDown") {
            e.preventDefault();
            if (suggestions.length > 0) {
                selectedSuggestionIndex = (selectedSuggestionIndex + 1) % suggestions.length;
            }
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            if (suggestions.length > 0) {
                selectedSuggestionIndex = (selectedSuggestionIndex - 1 + suggestions.length) % suggestions.length;
            }
        }
    }
</script>

<div class="flex-1 flex flex-col pt-2">
    {#if config && !config.telephone_enabled}
        <div class="flex-1 flex flex-col items-center justify-center py-12 px-4">
            <div class="w-full max-w-md bg-sem-surface border border-sem-border rounded-2xl p-8 flex flex-col items-center text-center shadow-xl">
                <div class="size-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mb-4">
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
    {:else if config?.telephone_enabled}
        {#if callMinimized && activeCall}
            <div class="w-full shrink-0 border-b border-sem-border">
                <div class="flex items-center gap-3 px-4 py-2 bg-blue-50/80 dark:bg-blue-900/20 backdrop-blur-xs">
                    <div class="relative">
                        <div class="size-8 rounded-full bg-sem-surface-muted flex items-center justify-center overflow-hidden">
                            <LxmfUserIcon
                                customImage={activeCall.custom_image || undefined}
                                iconName={activeCall.remote_icon?.icon_name || "account"}
                                iconForegroundColour={activeCall.remote_icon?.foreground_colour || ""}
                                iconBackgroundColour={activeCall.remote_icon?.background_colour || ""}
                                iconClass="size-7"
                            />
                        </div>
                        <div class="absolute -bottom-0.5 -right-0.5 size-2.5 bg-green-500 rounded-full border-2 border-white dark:border-zinc-900"></div>
                    </div>
                    <div class="flex-1 min-w-0">
                        <div class="text-sm font-bold text-sem-fg truncate">
                            {activeCall.remote_identity_name || t("call.unknown")}
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
                            onclick={() => (callMinimized = false)}
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

        {#if isSessionActive}
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
                onminimize={() => (callMinimized = true)}
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
                                        onkeydown={handleInputKeydown}
                                        onfocus={() => (isCallInputFocused = true)}
                                        onblur={() => setTimeout(() => (isCallInputFocused = false), 200)}
                                    />
                                    {#if isCallInputFocused && suggestions.length > 0}
                                        <div class="absolute z-50 left-0 right-0 mt-1 bg-sem-surface border border-sem-border rounded-xl shadow-xl overflow-hidden">
                                            {#each suggestions as suggestion, index (suggestion.hash)}
                                                <button
                                                    type="button"
                                                    class="w-full text-left px-4 py-2.5 flex items-center gap-3 cursor-pointer transition-colors {index === selectedSuggestionIndex ? 'bg-blue-50 dark:bg-blue-900/30 text-sem-accent' : 'hover:bg-sem-surface-muted/50 text-sem-fg-muted'}"
                                                    onmousedown={(e) => {
                                                        e.preventDefault();
                                                        onselectsuggestion?.(suggestion);
                                                    }}
                                                >
                                                    <div class="shrink-0 size-8 rounded-full flex items-center justify-center text-xs {suggestion.type === 'contact' ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-600' : 'bg-sem-surface-muted text-gray-500'}">
                                                        <MaterialDesignIcon iconName={suggestion.icon || "account"} class="size-4" />
                                                    </div>
                                                    <div class="flex-1 min-w-0">
                                                        <div class="text-sm font-bold truncate">{suggestion.name}</div>
                                                        <div class="text-[10px] font-mono opacity-50 truncate hover:text-blue-500 transition-colors cursor-copy" title={suggestion.hash}>
                                                            {formatDestinationHash(suggestion.hash)}
                                                        </div>
                                                    </div>
                                                    {#if suggestion.type === "contact"}
                                                        <div class="text-[10px] uppercase font-bold tracking-widest opacity-30">Contact</div>
                                                    {/if}
                                                </button>
                                            {/each}
                                        </div>
                                    {/if}
                                </div>
                                <button
                                    type="button"
                                    class="bg-blue-600 hover:bg-blue-500 text-white px-6 rounded-2xl font-bold shadow-lg shadow-blue-500/20 transition-all flex items-center gap-2"
                                    onclick={handleCallSubmit}
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
                            onchangeaudioprofile={onselectaudioprofile}
                            onchangecallmode={onselectcallmode}
                            onselectaudioinput={onselectaudioinput}
                            onselectaudiooutput={onselectaudiooutput}
                            {onrefreshaudiodevices}
                            {onrestartwebaudio}
                        />
                    </div>
                </div>

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
                    {onaddcontact}
                    {onblockidentity}
                    {onopenmessage}
                    {oncallback}
                    onloadmore={onloadmorehistory}
                    {oncopyhash}
                />
            </div>
        {/if}
    {/if}
</div>
