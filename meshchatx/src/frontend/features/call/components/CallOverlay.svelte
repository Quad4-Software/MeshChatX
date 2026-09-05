<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import LxmfUserIcon from "../../../ui/svelte/LxmfUserIcon.svelte";
    import CallOverlayControls from "./CallOverlayControls.svelte";
    import { t } from "../../../js/i18n.js";
    import { safeFade } from "../lib/callTransitions.js";
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
    } from "../lib/callOverlayLogic.js";

    let {
        activeCall = null,
        isEnded = false,
        wasDeclined = false,
        voicemailStatus: _voicemailStatus = null,
        initiationStatus = null,
        initiationTargetHash = null,
        initiationTargetName = null,
        activeCallTab: _activeCallTab = null,
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
    const remoteDisplayName = $derived(
        (activeCall ? activeCall.remote_identity_name : initiationTargetName) || t("call.unknown")
    );
    const remoteHashFormatted = $derived(
        formatDestinationHash(activeCall ? activeCall.remote_identity_hash : initiationTargetHash)
    );
    const currentElapsedTime = $derived(
        elapsedTime !== null ? elapsedTime : calculateElapsedTime(activeCall?.call_start_time, now)
    );
    const currentCallDuration = $derived(
        callDuration !== null ? callDuration : calculateCallDuration(isEnded, activeCall?.call_start_time, now)
    );
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

    async function handleToggleMic() {
        localMicMuted = await executeToggleMicrophone({
            isCurrentlyMuted: localMicMuted,
            onmute,
            ontogglemic,
        });
    }

    async function handleToggleSpeaker() {
        localSpeakerMuted = await executeToggleSpeaker({
            isCurrentlyMuted: localSpeakerMuted,
            ontogglespeaker,
        });
    }

    async function handleToggleDuplex() {
        const result = await executeToggleDuplexMode(activeCall, localHalfDuplex);
        if (result) {
            localPttActive = result.isPttActive;
            localHalfDuplex = result.isHalfDuplex;
        }
    }

    async function handleSetPtt(active: boolean) {
        localPttActive = active;
        await executeSetPttActive(active, activeCall, localHalfDuplex);
    }
</script>

{#if !isMinimized}
    <aside
        aria-label={t("call.active_call_overlay")}
        transition:safeFade={{ duration: 120 }}
        class="fixed z-90 w-[min(20rem,calc(100%-1.5rem))] max-sm:left-1/2 max-sm:-translate-x-1/2 max-sm:right-auto sm:right-4 bottom-[max(1rem,env(safe-area-inset-bottom,0px))] max-sm:bottom-[calc(5.5rem+env(safe-area-inset-bottom,0px))] bg-sem-surface/95 backdrop-blur-md rounded-2xl shadow-2xl border border-sem-border overflow-hidden transition-all duration-300 animate-slide-up"
    >
        <div class="px-4 py-3 bg-sem-surface-muted/50 border-b border-sem-border flex items-center justify-between">
            <div class="flex items-center space-x-2">
                <span class="relative flex h-2 w-2">
                    <span class="animate-ping absolute inline-flex h-full w-full rounded-full {statusColor} opacity-75"
                    ></span>
                    <span class="relative inline-flex rounded-full h-2 w-2 {statusColor}"></span>
                </span>
                <span class="text-xs font-bold uppercase tracking-wider text-sem-fg-muted">{headerStatus}</span>
            </div>
            <div class="flex items-center space-x-1">
                <button
                    type="button"
                    title={t("call.minimize")}
                    class="p-1 rounded-lg text-sem-fg-muted hover:text-sem-fg hover:bg-sem-surface-muted transition-colors cursor-pointer focus-ring-sem"
                    onclick={toggleMinimized}
                >
                    <MaterialDesignIcon iconName="minus" class="size-4" />
                </button>
                <button
                    type="button"
                    title={t("call.go_to_phone_page")}
                    class="p-1 rounded-lg text-sem-fg-muted hover:text-sem-fg hover:bg-sem-surface-muted transition-colors cursor-pointer focus-ring-sem"
                    onclick={goToPhonePage}
                >
                    <MaterialDesignIcon iconName="open-in-new" class="size-4" />
                </button>
            </div>
        </div>

        <div class="p-6 text-center">
            <div class="relative inline-block mb-4">
                <div
                    class="rounded-2xl p-1 bg-gradient-to-tr from-sem-accent to-sem-accent/70 shadow-lg shadow-sem-accent/20"
                >
                    <LxmfUserIcon
                        customImage={typeof activeCall?.remote_custom_image === "string"
                            ? activeCall.remote_custom_image
                            : undefined}
                        iconName={activeCall?.remote_icon?.icon_name || ""}
                        iconForegroundColour={activeCall?.remote_icon?.foreground_colour || ""}
                        iconBackgroundColour={activeCall?.remote_icon?.background_colour || ""}
                        iconClass="size-16 rounded-xl"
                    />
                </div>
            </div>

            <h4 class="text-lg font-bold text-sem-fg truncate px-2">{remoteDisplayName}</h4>
            <p class="text-xs text-sem-fg-muted font-mono truncate mb-2">{remoteHashFormatted}</p>
            <div
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-sem-accent-subtle text-sem-accent mb-4"
            >
                {callStatusLabel}
            </div>

            <div class="text-3xl font-mono font-bold text-sem-fg mb-6 tracking-wider">
                {isEnded ? currentCallDuration : currentElapsedTime}
            </div>

            {#if activeCall?.status === 6}
                <div
                    class="grid grid-cols-2 gap-2 text-[10px] text-sem-fg-muted bg-sem-surface-muted/50 p-2 rounded-xl mb-6"
                >
                    <div class="flex flex-col items-center">
                        <span class="uppercase tracking-wider font-medium">{t("call.sent")}</span>
                        <span class="font-mono font-bold text-sem-fg"
                            >{formatBytes(Number(activeCall.audio_bytes_sent || 0))}</span
                        >
                    </div>
                    <div class="flex flex-col items-center">
                        <span class="uppercase tracking-wider font-medium">{t("call.received")}</span>
                        <span class="font-mono font-bold text-sem-fg"
                            >{formatBytes(Number(activeCall.audio_bytes_received || 0))}</span
                        >
                    </div>
                </div>
            {/if}

            <CallOverlayControls
                {activeCall}
                {localHalfDuplex}
                {localMicMuted}
                {localSpeakerMuted}
                {localPttActive}
                {isEnded}
                {wasDeclined}
                ontoggleduplex={handleToggleDuplex}
                ontogglemic={handleToggleMic}
                ontogglespeaker={handleToggleSpeaker}
                onhangup={handleHangup}
                onsendtovoicemail={handleSendToVoicemail}
                onanswer={handleAnswer}
                onsetptt={handleSetPtt}
            />
        </div>
    </aside>
{/if}
