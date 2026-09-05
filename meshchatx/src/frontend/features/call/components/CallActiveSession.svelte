<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import LxmfUserIcon from "../../../ui/svelte/LxmfUserIcon.svelte";
    import {
        formatDestinationHash as defaultFormatHash,
        formatNumber as defaultFormatNum,
        formatBytes as defaultFormatB,
        formatBitrate as defaultFormatBr,
    } from "../lib/callFormat.js";
    import { t } from "../../../js/i18n.js";

    interface Props {
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
        audioProfiles?: Array<{ id: number | string; name: string }>;
        callModes?: Array<{ id: number | string; name: string }>;
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

    let {
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
        audioProfiles = [],
        callModes = [],
        selectedAudioProfileId = "",
        selectedCallModeId = "",
        isMicMuted = false,
        isSpeakerMuted = false,
        localPttActive = false,
        isHalfDuplexCall = false,
        playingVoicemailId = null,
        formatDestinationHash = defaultFormatHash,
        formatNumber = defaultFormatNum,
        formatBytes = defaultFormatB,
        formatBitrate = defaultFormatBr,
        onplaylatestvoicemail,
        onselectaudioprofile,
        onselectcallmode,
        ontogglemic,
        ontogglespeaker,
        onsetptt,
        onanswer,
        onsendtovoicemail,
        onminimize,
        onhangup,
    }: Props = $props();

    const currentPeer = $derived(activeCall || lastCall);
    const peerName = $derived(currentPeer?.remote_identity_name || initiationTargetName || t("call.unknown"));
    const peerHash = $derived(currentPeer?.remote_identity_hash || initiationTargetHash || "");
</script>

{#snippet statCard(label: string, value: string)}
    <div
        class="rounded-xl bg-gray-50 dark:bg-zinc-800/70 border border-gray-100 dark:border-zinc-700/70 px-2 py-1.5 text-left"
    >
        <div class="text-[10px] text-sem-fg-muted">{label}</div>
        <div class="font-semibold text-sem-fg">{value}</div>
    </div>
{/snippet}

<div class="flex-1 flex flex-col items-center justify-center py-12 px-4">
    <div
        class="w-full max-w-md border-b border-sem-border p-8! flex flex-col items-center text-center relative overflow-hidden"
    >
        {#if activeCall?.is_recording}
            <div
                class="absolute top-4 right-4 z-20 flex items-center gap-1.5 px-2 py-1 bg-red-500/10 rounded-full border border-red-500/20"
            >
                <div class="size-2 bg-red-500 rounded-full animate-pulse"></div>
                <span class="text-[10px] font-bold text-red-500 uppercase tracking-wider">Recording</span>
            </div>
        {/if}

        <div class="relative mb-8">
            <div
                class="size-32 mx-auto bg-sem-surface-muted rounded-full flex items-center justify-center border-4 border-white dark:border-zinc-900 shadow-2xl relative z-10 {activeCall?.status ===
                4
                    ? 'ring-4 ring-blue-500/20 animate-pulse'
                    : ''}"
            >
                <LxmfUserIcon
                    customImage={currentPeer?.custom_image}
                    iconName={currentPeer?.remote_icon?.icon_name || ""}
                    iconForegroundColour={currentPeer?.remote_icon?.foreground_colour || ""}
                    iconBackgroundColour={currentPeer?.remote_icon?.background_colour || ""}
                    iconClass="size-28"
                />
            </div>

            {#if activeCall?.status === 6}
                <div
                    class="absolute -bottom-2 -right-2 bg-green-500 text-white p-2 rounded-full shadow-lg border-4 border-white dark:border-zinc-900 z-20"
                >
                    <MaterialDesignIcon iconName="phone-in-talk" class="size-5" />
                </div>
            {/if}
        </div>

        <div class="relative z-10 space-y-1 mb-8 flex flex-col items-center text-center">
            <h2 class="text-2xl font-bold text-sem-fg truncate max-w-[280px]">{peerName}</h2>
            {#if peerHash}
                <div class="text-xs font-mono text-sem-fg-muted tracking-wider">
                    {formatDestinationHash(peerHash)}
                </div>
            {/if}
            {#if activeCall}
                <div class="mt-1 flex items-center justify-center gap-2 text-[11px] text-sem-fg-muted">
                    {#if activeCall.path_hops != null}
                        <span class="inline-flex items-center gap-1 rounded-full bg-sem-surface-muted px-2 py-0.5">
                            <MaterialDesignIcon iconName="sitemap-outline" class="size-4" />
                            {activeCall.path_hops} hops
                        </span>
                    {/if}
                    {#if activeCall.path_interface}
                        <span
                            class="inline-flex items-center gap-1 rounded-full bg-sem-surface-muted px-2 py-0.5 max-w-[16rem]"
                        >
                            <MaterialDesignIcon iconName="access-point-network" class="size-4" />
                            <span class="truncate">{activeCall.path_interface}</span>
                        </span>
                    {/if}
                </div>
            {/if}
            {#if currentPeer?.is_contact || !!initiationTargetName}
                <div
                    class="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-50 dark:bg-blue-900/30 text-sem-accent text-[10px] font-bold rounded-full uppercase tracking-wider"
                >
                    <MaterialDesignIcon iconName="check-decagram" class="size-3" />
                    Contact
                </div>
            {/if}
        </div>

        <div class="relative z-10 mb-8">
            <div
                class="px-4 py-2 bg-gray-50 dark:bg-zinc-800/50 rounded-2xl inline-block border border-sem-border"
            >
                {#if wasDeclined}
                    <span class="text-red-500 font-bold text-sm">{t("call.call_declined")}</span>
                {:else if isCallEnded}
                    <span class="text-sem-fg-muted font-bold text-sm">{t("call.call_ended")}</span>
                {:else if activeCall}
                    <div class="flex flex-col items-center">
                        {#if activeCall.is_voicemail}
                            <span class="text-red-500 font-bold text-sm animate-pulse flex items-center gap-2">
                                <MaterialDesignIcon iconName="record" class="size-4" />
                                {t("call.recording_voicemail")}
                            </span>
                        {:else if activeCall.is_incoming && activeCall.status === 4}
                            <span class="text-sem-accent font-bold text-sm">{t("call.incoming_call")}</span>
                        {:else}
                            <span class="text-sem-fg-muted font-bold text-sm flex items-center gap-2">
                                {#if activeCall.status === 0}
                                    <span>Busy...</span>
                                {:else if activeCall.status === 1}
                                    <span class="text-red-500">Rejected</span>
                                {:else if activeCall.status === 2}
                                    <span class="animate-pulse">Calling...</span>
                                {:else if activeCall.status === 3}
                                    <span>Available</span>
                                {:else if activeCall.status === 4}
                                    <span class="animate-pulse">Ringing...</span>
                                {:else if activeCall.status === 5}
                                    <span>{t("call.establishing_link")}</span>
                                {:else if activeCall.status === 6}
                                    <span class="text-green-500 flex items-center gap-2">
                                        <span class="size-2 bg-green-500 rounded-full animate-ping"></span>
                                        Connected
                                    </span>
                                {:else}
                                    <span>Status: {activeCall.status}</span>
                                {/if}
                            </span>

                            {#if activeCall.status === 6 && elapsedTime}
                                <div class="text-xs font-mono text-sem-fg-muted mt-1">{elapsedTime}</div>
                            {/if}

                            {#if activeCall.status === 6}
                                <div class="mt-3 grid grid-cols-2 gap-2 text-xs w-full max-w-xs">
                                    {@render statCard(t("call.tx_packets"), formatNumber(activeCall.tx_packets))}
                                    {@render statCard(t("call.rx_packets"), formatNumber(activeCall.rx_packets))}
                                    {@render statCard(t("call.tx_data"), formatBytes(activeCall.tx_bytes))}
                                    {@render statCard(t("call.rx_data"), formatBytes(activeCall.rx_bytes))}
                                    {@render statCard(t("call.tx_rate"), formatBitrate(activeCall.tx_bps))}
                                    {@render statCard(t("call.rx_rate"), formatBitrate(activeCall.rx_bps))}
                                </div>

                                <div class="mt-2 text-[10px] font-semibold uppercase tracking-wider text-sem-fg-muted">
                                    {activeCall.is_half_duplex ? t("call.half_duplex") : t("call.full_duplex")}
                                    {#if activeCall.is_half_duplex}
                                        <span>
                                            · {localPttActive ? t("call.ptt_transmitting") : t("call.ptt_listening")}
                                        </span>
                                    {/if}
                                </div>
                            {/if}
                        {/if}
                    </div>
                {:else if initiationStatus}
                    <div class="flex flex-col items-center">
                        <span class="text-sem-accent font-bold text-sm animate-pulse">{initiationStatus}</span>
                    </div>
                {/if}
            </div>

            {#if isCallEnded && callDuration}
                <div class="text-xs font-mono text-sem-fg-muted mt-2">Duration: {callDuration}</div>
            {/if}

            {#if isCallEnded && wasVoicemail}
                <div class="mt-6 animate-fade-in">
                    <button
                        type="button"
                        class="px-6 py-3 rounded-full bg-blue-500 hover:bg-blue-600 text-white font-bold flex items-center gap-2 shadow-lg shadow-blue-500/30 transition-all hover:scale-105"
                        onclick={() => onplaylatestvoicemail?.()}
                    >
                        <MaterialDesignIcon iconName={playingVoicemailId ? "stop" : "play"} class="size-6" />
                        <span>{playingVoicemailId ? "Stop" : "Play Voicemail"}</span>
                    </button>
                </div>
            {/if}
        </div>

        {#if activeCall && activeCall.status === 6}
            <div class="w-full relative z-10 mb-8">
                <div class="flex flex-col gap-4">
                    <select
                        value={selectedAudioProfileId}
                        class="input-field rounded-xl! py-2! shadow-xs"
                        onchange={(e) => onselectaudioprofile?.((e.target as HTMLSelectElement).value)}
                    >
                        {#each audioProfiles as audioProfile (audioProfile.id)}
                            <option value={audioProfile.id}>{audioProfile.name}</option>
                        {/each}
                    </select>

                    <select
                        value={selectedCallModeId}
                        class="input-field rounded-xl! py-2! shadow-xs"
                        onchange={(e) => onselectcallmode?.((e.target as HTMLSelectElement).value)}
                    >
                        {#each callModes as callMode (callMode.id)}
                            <option value={callMode.id}>{callMode.name}</option>
                        {/each}
                    </select>

                    <div class="flex justify-center gap-4">
                        <button
                            type="button"
                            title={isMicMuted ? t("call.unmute_mic") : t("call.mute_mic")}
                            class="p-4 rounded-full shadow-lg transition-all duration-200 {isMicMuted
                                ? 'bg-red-500 text-white shadow-red-500/20'
                                : 'bg-sem-surface-muted text-sem-fg-secondary hover:bg-gray-200 hover:bg-sem-surface-muted shadow-gray-200/20 dark:shadow-black/20'}"
                            onclick={() => ontogglemic?.()}
                        >
                            <MaterialDesignIcon iconName={isMicMuted ? "microphone-off" : "microphone"} class="size-6" />
                        </button>

                        <button
                            type="button"
                            title={isSpeakerMuted ? t("call.unmute_speaker") : t("call.mute_speaker")}
                            class="p-4 rounded-full shadow-lg transition-all duration-200 {isSpeakerMuted
                                ? 'bg-red-500 text-white shadow-red-500/20'
                                : 'bg-sem-surface-muted text-sem-fg-secondary hover:bg-gray-200 hover:bg-sem-surface-muted shadow-gray-200/20 dark:shadow-black/20'}"
                            onclick={() => ontogglespeaker?.()}
                        >
                            <MaterialDesignIcon iconName={isSpeakerMuted ? "volume-off" : "volume-high"} class="size-6" />
                        </button>
                    </div>

                    {#if isHalfDuplexCall}
                        <button
                            type="button"
                            class="w-full flex items-center justify-center gap-2 rounded-2xl py-5 text-base font-bold text-white shadow-xl transition-all duration-150 select-none touch-none {localPttActive
                                ? 'bg-amber-500 shadow-amber-500/30 scale-[1.02]'
                                : 'bg-blue-600 shadow-blue-600/20 hover:bg-blue-500'}"
                            title={t("call.ptt_hold_hint")}
                            onpointerdown={(e) => {
                                e.preventDefault();
                                onsetptt?.(true);
                            }}
                            onpointerup={(e) => {
                                e.preventDefault();
                                onsetptt?.(false);
                            }}
                            onpointerleave={() => onsetptt?.(false)}
                            onpointercancel={() => onsetptt?.(false)}
                        >
                            <MaterialDesignIcon
                                iconName={localPttActive ? "microphone" : "access-point-network"}
                                class="size-7"
                            />
                            <span>
                                {localPttActive ? t("call.ptt_transmitting") : t("call.ptt_hold_to_talk")}
                            </span>
                        </button>
                        <div class="text-center text-[11px] text-sem-fg-muted">
                            {t("call.ptt_spacebar_hint")}
                        </div>
                    {/if}
                </div>
            </div>
        {/if}

        {#if activeCall}
            <div class="w-full relative z-10 flex flex-col gap-3">
                {#if activeCall.is_incoming && activeCall.status === 4}
                    <div class="flex gap-3">
                        <button
                            type="button"
                            class="flex-1 flex items-center justify-center gap-2 rounded-2xl bg-green-600 py-4 text-sm font-bold text-white shadow-xl shadow-green-600/20 hover:bg-green-500 transition-all duration-200"
                            onclick={() => onanswer?.()}
                        >
                            <MaterialDesignIcon iconName="phone" class="size-5" />
                            <span>{t("call.accept")}</span>
                        </button>

                        <button
                            type="button"
                            class="flex-1 flex items-center justify-center gap-2 rounded-2xl bg-blue-600 py-4 text-sm font-bold text-white shadow-xl shadow-blue-600/20 hover:bg-blue-500 transition-all duration-200"
                            onclick={() => onsendtovoicemail?.()}
                        >
                            <MaterialDesignIcon iconName="voicemail" class="size-5" />
                            <span>Voicemail</span>
                        </button>
                    </div>
                {/if}

                <button
                    type="button"
                    class="flex items-center justify-center gap-2 rounded-2xl bg-sem-surface-muted py-3 px-4 text-sm font-bold text-sem-fg-muted hover:bg-gray-200 hover:bg-sem-surface-muted transition-all duration-200"
                    onclick={() => onminimize?.()}
                >
                    <MaterialDesignIcon iconName="chevron-down" class="size-5" />
                    <span>{t("call.minimize")}</span>
                </button>

                <button
                    type="button"
                    class="w-full flex items-center justify-center gap-2 rounded-2xl bg-red-600 py-4 text-sm font-bold text-white shadow-xl shadow-red-600/20 hover:bg-red-500 transition-all duration-200"
                    onclick={() => onhangup?.()}
                >
                    <MaterialDesignIcon iconName="phone-hangup" class="size-5 rotate-135" />
                    <span>
                        {activeCall.is_incoming && activeCall.status === 4
                            ? t("call.decline")
                            : t("call.hangup")}
                    </span>
                </button>
            </div>
        {/if}
    </div>
</div>
