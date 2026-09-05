<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import LxmfUserIcon from "../../../ui/svelte/LxmfUserIcon.svelte";
    import AudioWaveformPlayer from "../../messages/components/AudioWaveformPlayer.svelte";
    import { t } from "../../../js/i18n.js";
    import {
        getHeaderStatusText,
        getCallStatusLabel,
        formatDestinationHash,
        formatBytes,
        calculateElapsedTime,
        calculateCallDuration,
        getStatusColorClass,
        executeAnswerCall,
        executeHangupCall,
        executeSendToVoicemail,
        executeToggleMicrophone,
        executeToggleSpeaker,
        executeToggleDuplexMode,
        executeSetPttActive,
        type CallOverlayProps,
    } from "../lib/callOverlayLogic";

    let {
        activeCall = null,
        isEnded = false,
        wasDeclined = false,
        voicemailStatus = null,
        initiationStatus = null,
        initiationTargetHash = null,
        initiationTargetName = null,
        activeCallTab = null,
        elapsedTime = null,
        callDuration = null,
        isMinimized = $bindable(false),
        router = undefined,
        route = undefined,
        onanswer = undefined,
        onhangup = undefined,
        onmute = undefined,
        ontogglemic = undefined,
        ontogglespeaker = undefined,
        onexpand = undefined,
        ongotophone = undefined,
    }: CallOverlayProps = $props();

    let localMicMuted = $state(false);
    let localSpeakerMuted = $state(false);
    let localPttActive = $state(false);
    let localHalfDuplex = $state(false);
    let previousCallHash = $state<string | null>(null);
    let now = $state(Date.now());

    $effect(() => {
        const interval = setInterval(() => {
            now = Date.now();
        }, 1000);
        return () => clearInterval(interval);
    });

    $effect(() => {
        const currentCall = activeCall;
        if (currentCall) {
            if (!previousCallHash || currentCall.hash !== previousCallHash) {
                localMicMuted = Boolean(currentCall.is_mic_muted);
                localSpeakerMuted = Boolean(currentCall.is_speaker_muted);
                localPttActive = Boolean(currentCall.is_ptt_active);
                localHalfDuplex = Boolean(currentCall.is_half_duplex);
                previousCallHash = currentCall.hash ?? null;
            } else {
                localPttActive = Boolean(currentCall.is_ptt_active);
                localHalfDuplex = Boolean(currentCall.is_half_duplex);
            }
        } else {
            localPttActive = false;
            localHalfDuplex = false;
            previousCallHash = null;
        }
    });

    const headerStatus = $derived(getHeaderStatusText({ wasDeclined, isEnded, activeCall, initiationStatus }));
    const callStatusLabel = $derived(getCallStatusLabel({ activeCall, wasDeclined, isEnded }));
    const remoteDisplayName = $derived((activeCall ? activeCall.remote_identity_name : initiationTargetName) || t("call.unknown"));
    const remoteHashFormatted = $derived(formatDestinationHash(activeCall ? activeCall.remote_identity_hash : initiationTargetHash));
    const currentElapsedTime = $derived(elapsedTime !== null ? elapsedTime : calculateElapsedTime(activeCall?.call_start_time, now));
    const currentCallDuration = $derived(callDuration !== null ? callDuration : calculateCallDuration(isEnded, activeCall?.call_start_time, now));
    const statusColor = $derived(getStatusColorClass({ wasDeclined, isEnded, activeCall }));

    function toggleMinimized() {
        isMinimized = !isMinimized;
        if (!isMinimized && onexpand) onexpand();
    }

    function goToPhonePage() {
        if (ongotophone) {
            ongotophone();
            return;
        }
        if (router?.push) {
            router.push({ name: "call", query: { tab: "phone" } });
        }
    }

    async function handleAnswer() {
        await executeAnswerCall({ router, route, onanswer, ongotophone });
    }

    async function handleHangup() {
        await executeHangupCall({ onhangup });
    }

    async function handleSendToVoicemail() {
        await executeSendToVoicemail();
    }

    async function handleToggleMicrophone() {
        localMicMuted = await executeToggleMicrophone({ isCurrentlyMuted: localMicMuted, onmute, ontogglemic });
    }

    async function handleToggleSpeaker() {
        localSpeakerMuted = await executeToggleSpeaker({ isCurrentlyMuted: localSpeakerMuted, ontogglespeaker });
    }

    async function handleToggleDuplex() {
        const result = await executeToggleDuplexMode(activeCall, localHalfDuplex);
        if (result) {
            localPttActive = result.isPttActive;
            localHalfDuplex = result.isHalfDuplex;
        }
    }

    async function handleSetPtt(active: boolean) {
        localPttActive = await executeSetPttActive(active, activeCall, localHalfDuplex);
    }
</script>

{#if activeCall || initiationStatus || isEnded || wasDeclined}
    <div
        class="fixed z-90 w-[min(20rem,calc(100%-1.5rem))] max-sm:left-1/2 max-sm:-translate-x-1/2 max-sm:right-auto sm:right-4 bottom-[max(1rem,env(safe-area-inset-bottom,0px))] max-sm:bottom-[calc(5.5rem+env(safe-area-inset-bottom,0px))] bg-sem-surface rounded-2xl shadow-2xl border border-sem-border overflow-hidden transition-all duration-300 {isEnded || wasDeclined ? 'ring-2 ring-red-500 ring-opacity-50' : ''}"
    >
        <!-- Header -->
        <div class="p-3 flex items-center bg-gray-50 dark:bg-zinc-800/50 border-b border-sem-border">
            <div class="flex-1 flex items-center space-x-2">
                <div class="size-2 rounded-full {isEnded || wasDeclined ? 'bg-red-500' : 'bg-green-500 animate-pulse'}"></div>
                <button
                    type="button"
                    class="flex items-center space-x-2 hover:opacity-70 transition-opacity group"
                    title={t("call.go_to_phone_page")}
                    onclick={goToPhonePage}
                >
                    <span class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-wider group-hover:text-gray-700 dark:group-hover:text-zinc-200">
                        {headerStatus}
                    </span>
                    <MaterialDesignIcon iconName="open-in-new" class="size-3 text-sem-fg-muted group-hover:text-gray-600 dark:group-hover:text-zinc-300" />
                </button>
                {#if activeCall?.is_recording && !isEnded}
                    <div class="flex items-center gap-1 ml-2">
                        <div class="size-1.5 bg-red-500 rounded-full animate-pulse"></div>
                        <span class="text-[8px] font-bold text-red-500 uppercase tracking-tighter">REC</span>
                    </div>
                {/if}
            </div>
            {#if !isEnded}
                <button
                    type="button"
                    class="p-1 hover:bg-gray-200 hover:bg-sem-surface-muted rounded-lg transition-colors"
                    onclick={toggleMinimized}
                >
                    <MaterialDesignIcon iconName={isMinimized ? "chevron-up" : "chevron-down"} class="size-4 text-gray-500" />
                </button>
            {/if}
        </div>

        <!-- Body -->
        {#if !isMinimized}
            <div class="p-4">
                <div class="flex flex-col items-center mb-4">
                    <div class="p-2 rounded-full mb-3 {isEnded || wasDeclined ? 'bg-red-100 dark:bg-red-900/30' : 'bg-blue-100 dark:bg-blue-900/30'}">
                        <LxmfUserIcon
                            customImage={activeCall?.custom_image || ""}
                            iconName={activeCall?.remote_icon?.icon_name || ""}
                            iconForegroundColour={activeCall?.remote_icon?.foreground_colour || ""}
                            iconBackgroundColour={activeCall?.remote_icon?.background_colour || ""}
                            iconClass="size-14"
                        />
                    </div>
                    <div class="text-center w-full min-w-0">
                        <div class="font-bold text-sem-fg truncate px-2">{remoteDisplayName}</div>
                        {#if activeCall?.is_contact || initiationTargetName}
                            <div class="text-[10px] text-sem-accent font-medium mt-0.5">In contacts</div>
                        {/if}
                        <div class="text-[10px] text-sem-fg-muted font-mono truncate px-4">{remoteHashFormatted}</div>
                    </div>
                </div>

                <div class="text-center mb-6">
                    {#if activeCall}
                        <div class="text-sm font-medium {statusColor}">
                            {#if activeCall.is_voicemail && !wasDeclined && !isEnded}
                                <span class="flex items-center justify-center gap-2">
                                    <MaterialDesignIcon iconName="record" class="size-4" />
                                    {callStatusLabel}
                                </span>
                            {:else}
                                <span>{callStatusLabel}</span>
                            {/if}
                        </div>
                    {:else if initiationStatus}
                        <div class="text-sm font-medium text-sem-accent animate-pulse">{initiationStatus}</div>
                    {/if}
                    {#if activeCall?.status === 6 && !isEnded && currentElapsedTime}
                        <div class="text-xs text-sem-fg-muted mt-1 font-mono">{currentElapsedTime}</div>
                    {/if}
                    {#if isEnded && currentCallDuration}
                        <div class="text-xs text-sem-fg-muted mt-1 font-mono">{currentCallDuration}</div>
                    {/if}
                </div>

                {#if activeCall?.status === 6 && !isEnded}
                    <div class="mb-4 p-2 bg-gray-50 dark:bg-zinc-800/50 rounded-lg text-[10px] text-sem-fg-muted grid grid-cols-2 gap-1">
                        <div class="flex items-center space-x-1">
                            <MaterialDesignIcon iconName="arrow-up" class="size-3" />
                            <span>{formatBytes(activeCall.tx_bytes || 0)}</span>
                        </div>
                        <div class="flex items-center space-x-1">
                            <MaterialDesignIcon iconName="arrow-down" class="size-3" />
                            <span>{formatBytes(activeCall.rx_bytes || 0)}</span>
                        </div>
                        <div class="col-span-2 text-center font-semibold uppercase tracking-wider">
                            {localHalfDuplex ? t("call.half_duplex") : t("call.full_duplex")}
                            {#if localHalfDuplex}
                                <span>· {localPttActive ? t("call.ptt_transmitting") : t("call.ptt_listening")}</span>
                            {/if}
                        </div>
                    </div>
                {/if}

                {#if !isEnded && !wasDeclined}
                    <div class="flex flex-wrap justify-center gap-2 px-2">
                        {#if activeCall?.status === 6}
                            <button
                                type="button"
                                title={localHalfDuplex ? t("call.switch_to_full_duplex") : t("call.switch_to_half_duplex")}
                                class="p-2.5 rounded-full transition-all duration-200 bg-sem-surface-muted text-sem-fg-muted hover:bg-gray-200 hover:bg-sem-surface-muted"
                                onclick={handleToggleDuplex}
                            >
                                <MaterialDesignIcon iconName={localHalfDuplex ? "access-point-network" : "swap-horizontal"} class="size-5" />
                            </button>
                        {/if}
                        <button
                            type="button"
                            title={localMicMuted ? t("call.unmute_mic") : t("call.mute_mic")}
                            class="p-2.5 rounded-full transition-all duration-200 {localMicMuted ? 'bg-red-500 text-white shadow-lg shadow-red-500/30' : 'bg-sem-surface-muted text-sem-fg-muted hover:bg-gray-200 hover:bg-sem-surface-muted'}"
                            onclick={handleToggleMicrophone}
                        >
                            <MaterialDesignIcon iconName={localMicMuted ? "microphone-off" : "microphone"} class="size-5" />
                        </button>
                        <button
                            type="button"
                            title={localSpeakerMuted ? t("call.unmute_speaker") : t("call.mute_speaker")}
                            class="p-2.5 rounded-full transition-all duration-200 {localSpeakerMuted ? 'bg-red-500 text-white shadow-lg shadow-red-500/30' : 'bg-sem-surface-muted text-sem-fg-muted hover:bg-gray-200 hover:bg-sem-surface-muted'}"
                            onclick={handleToggleSpeaker}
                        >
                            <MaterialDesignIcon iconName={localSpeakerMuted ? "volume-off" : "volume-high"} class="size-5" />
                        </button>
                        <button
                            type="button"
                            title={activeCall?.is_incoming && activeCall.status === 4 ? t("call.decline_call") : t("call.hangup_call")}
                            class="p-2.5 rounded-full bg-red-600 text-white hover:bg-red-700 shadow-lg shadow-red-600/30 transition-all duration-200"
                            onclick={handleHangup}
                        >
                            <MaterialDesignIcon iconName="phone-hangup" class="size-5 rotate-135" />
                        </button>
                        {#if activeCall?.is_incoming && activeCall.status === 4}
                            <button
                                type="button"
                                title={t("call.send_to_voicemail")}
                                class="p-2.5 rounded-full bg-blue-600 text-white hover:bg-blue-700 shadow-lg shadow-blue-600/30 transition-all duration-200"
                                onclick={handleSendToVoicemail}
                            >
                                <MaterialDesignIcon iconName="voicemail" class="size-5" />
                            </button>
                            <button
                                type="button"
                                title={t("call.answer_call")}
                                class="p-2.5 rounded-full bg-green-600 text-white hover:bg-green-700 shadow-lg shadow-green-600/30"
                                onclick={handleAnswer}
                            >
                                <MaterialDesignIcon iconName="phone" class="size-5" />
                            </button>
                        {/if}
                    </div>

                    {#if activeCall?.status === 6 && localHalfDuplex && !isEnded}
                        <button
                            type="button"
                            class="mt-3 w-full flex items-center justify-center gap-2 rounded-xl py-3 text-sm font-bold text-white select-none touch-none {localPttActive ? 'bg-amber-500' : 'bg-blue-600'}"
                            onpointerdown={(e) => { e.preventDefault(); handleSetPtt(true); }}
                            onpointerup={(e) => { e.preventDefault(); handleSetPtt(false); }}
                            onpointerleave={() => handleSetPtt(false)}
                            onpointercancel={() => handleSetPtt(false)}
                        >
                            <MaterialDesignIcon iconName="microphone" class="size-5" />
                            <span>{localPttActive ? t("call.ptt_transmitting") : t("call.ptt_hold_to_talk")}</span>
                        </button>
                    {/if}
                {/if}
            </div>
        {/if}

        <!-- Ended voicemail playback -->
        {#if isEnded && activeCall?.is_voicemail && voicemailStatus?.latest_id}
            <div class="px-4 pb-4">
                <AudioWaveformPlayer src={`/api/v1/telephone/voicemails/${voicemailStatus.latest_id}/audio`} />
            </div>
        {/if}

        <!-- Minimized state -->
        {#if isMinimized && !isEnded}
            <div class="px-4 py-2 flex items-center justify-between bg-sem-surface">
                <div class="flex items-center space-x-2 overflow-hidden mr-2 min-w-0">
                    <LxmfUserIcon
                        customImage={activeCall?.custom_image || ""}
                        iconName={activeCall?.remote_icon?.icon_name || ""}
                        iconForegroundColour={activeCall?.remote_icon?.foreground_colour || ""}
                        iconBackgroundColour={activeCall?.remote_icon?.background_colour || ""}
                        iconClass="size-6 shrink-0"
                    />
                    <div class="flex flex-col min-w-0">
                        <span class="text-sm font-medium text-sem-fg-secondary truncate block">{remoteDisplayName}</span>
                        {#if activeCall?.status === 6 && currentElapsedTime}
                            <span class="text-[10px] text-sem-fg-muted font-mono">{currentElapsedTime}</span>
                        {/if}
                    </div>
                </div>
                <div class="flex items-center space-x-1">
                    <button
                        type="button"
                        class="p-1.5 hover:bg-sem-surface-muted rounded-sm transition-colors"
                        onclick={handleToggleMicrophone}
                    >
                        <MaterialDesignIcon iconName={localMicMuted ? "microphone-off" : "microphone"} class="size-4 {localMicMuted ? 'text-red-500' : 'text-gray-400'}" />
                    </button>
                    <button
                        type="button"
                        class="p-1.5 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-sm transition-colors"
                        onclick={handleHangup}
                    >
                        <MaterialDesignIcon iconName="phone-hangup" class="size-4 text-red-500 rotate-135" />
                    </button>
                </div>
            </div>
        {/if}
    </div>
{/if}
