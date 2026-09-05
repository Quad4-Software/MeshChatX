<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { fade } from "svelte/transition";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import LxmfUserIcon from "../../../ui/svelte/LxmfUserIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import { formatDestinationHash as defaultFormatHash } from "../lib/callFormat.js";
    import CallActiveSession from "./CallActiveSession.svelte";
    import CallDialer from "./CallDialer.svelte";
    import CallHistoryPanel from "./CallHistoryPanel.svelte";
    import type { CallPhoneTabProps } from "../lib/callUiTypes.js";

    let {
        active = true,
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
        contacts = [],
        callHistory = [],
        hasMoreCallHistory = false,
        callHistorySearch = "",
        isLoadingHistory = false,
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
    }: CallPhoneTabProps = $props();

    const transitionDuration = $derived(
        typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 120
    );

    const isSessionActive = $derived(Boolean((activeCall || isCallEnded || initiationStatus) && !callMinimized));
</script>

{#if active}
    <div class="flex-1 flex flex-col pt-2" transition:fade={{ duration: transitionDuration }}>
        {#if config && config.telephone_enabled === false}
            <div class="flex-1 flex flex-col items-center justify-center py-12 px-4">
                <div
                    class="w-full max-w-md bg-sem-surface border border-sem-border rounded-2xl p-8 flex flex-col items-center text-center shadow-xl"
                >
                    <div class="size-16 bg-sem-danger/10 rounded-full flex items-center justify-center mb-4">
                        <MaterialDesignIcon iconName="phone-off" class="size-8 text-sem-danger" />
                    </div>
                    <h2 class="text-xl font-bold text-sem-fg mb-2">{t("call.lxst_disabled_title")}</h2>
                    <p class="text-sm text-sem-fg-muted mb-6">{t("call.lxst_disabled_body")}</p>
                    <button
                        type="button"
                        class="primary-chip rounded-2xl! py-3! px-6! text-sm! focus-ring-sem cursor-pointer"
                        onclick={() => onupdateconfig?.({ telephone_enabled: true })}
                    >
                        <MaterialDesignIcon iconName="phone" class="size-5" />
                        {t("call.enable_lxst")}
                    </button>
                </div>
            </div>
        {:else}
            {#if callMinimized && activeCall}
                <div class="w-full shrink-0 border-b border-sem-border">
                    <div class="flex items-center gap-3 px-4 py-2 bg-sem-accent-subtle/40 backdrop-blur-xs">
                        <div class="relative">
                            <div
                                class="size-8 rounded-full bg-sem-surface-muted flex items-center justify-center overflow-hidden"
                            >
                                <LxmfUserIcon
                                    customImage={activeCall.custom_image || undefined}
                                    iconName={activeCall.remote_icon?.icon_name || "account"}
                                    iconForegroundColour={activeCall.remote_icon?.foreground_colour || ""}
                                    iconBackgroundColour={activeCall.remote_icon?.background_colour || ""}
                                    iconClass="size-7"
                                />
                            </div>
                            <div
                                class="absolute -bottom-0.5 -right-0.5 size-2.5 bg-emerald-500 rounded-full border-2 border-sem-surface"
                            ></div>
                        </div>
                        <div class="flex-1 min-w-0">
                            <div class="text-sm font-bold text-sem-fg truncate">
                                {activeCall.remote_identity_name || t("call.unknown")}
                            </div>
                            <div class="text-[10px] text-sem-fg-muted flex items-center gap-2">
                                <span class="size-1.5 bg-emerald-500 rounded-full animate-pulse"></span>
                                <span>{t("call.active")}</span>
                                {#if elapsedTime}
                                    <span class="font-mono">· {elapsedTime}</span>
                                {/if}
                            </div>
                        </div>
                        <div class="flex items-center gap-1 shrink-0">
                            <button
                                type="button"
                                class="size-8 flex items-center justify-center rounded-full hover:bg-sem-surface-muted transition-colors text-sem-fg-muted focus-ring-sem cursor-pointer"
                                title={t("call.expand_call")}
                                onclick={() => (callMinimized = false)}
                            >
                                <MaterialDesignIcon iconName="chevron-up" class="size-5" />
                            </button>
                            <button
                                type="button"
                                class="size-8 flex items-center justify-center rounded-full hover:bg-sem-danger/10 transition-colors text-sem-danger focus-ring-sem cursor-pointer"
                                title={t("call.hangup")}
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
                    <CallDialer
                        {destinationHash}
                        {contacts}
                        {callHistory}
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
                        {formatDestinationHash}
                        ondestinationchange={(val) => (destinationHash = val)}
                        {oncall}
                        {oncopyhash}
                        {ontogglednd}
                        {ontogglecontactsonly}
                        {ontoggletelephoneannounce}
                        {ontogglewebaudio}
                        onchangeaudioprofile={onselectaudioprofile}
                        onchangecallmode={onselectcallmode}
                        {onselectaudioinput}
                        {onselectaudiooutput}
                        {onrefreshaudiodevices}
                        {onrestartwebaudio}
                    />
                </div>
            {/if}

            <div class="mt-4">
                <CallHistoryPanel
                    {callHistory}
                    {hasMoreCallHistory}
                    {callHistorySearch}
                    isLoading={isLoadingHistory}
                    {getContactByHash}
                    {formatDestinationHash}
                    {formatDateTime}
                    {formatDuration}
                    onsearchinput={onhistorysearch}
                    onloadmore={onloadmorehistory}
                    {onclearhistory}
                    {onaddcontact}
                    {onblockidentity}
                    {onopenmessage}
                    {oncallback}
                    {oncopyhash}
                />
            </div>
        {/if}
    </div>
{/if}
