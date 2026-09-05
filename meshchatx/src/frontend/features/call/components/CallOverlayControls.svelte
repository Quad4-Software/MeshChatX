<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import type { ActiveCall } from "../lib/callOverlayLogic.js";

    interface Props {
        activeCall?: ActiveCall | null;
        localHalfDuplex?: boolean;
        localMicMuted?: boolean;
        localSpeakerMuted?: boolean;
        localPttActive?: boolean;
        isEnded?: boolean;
        wasDeclined?: boolean;
        ontoggleduplex?: () => void;
        ontogglemic?: () => void;
        ontogglespeaker?: () => void;
        onhangup?: () => void;
        onsendtovoicemail?: () => void;
        onanswer?: () => void;
        onsetptt?: (active: boolean) => void;
    }

    let {
        activeCall = null,
        localHalfDuplex = false,
        localMicMuted = false,
        localSpeakerMuted = false,
        localPttActive = false,
        isEnded = false,
        wasDeclined = false,
        ontoggleduplex,
        ontogglemic,
        ontogglespeaker,
        onhangup,
        onsendtovoicemail,
        onanswer,
        onsetptt,
    }: Props = $props();
</script>

{#if !isEnded && !wasDeclined}
    <div class="flex flex-wrap justify-center gap-2 px-2">
        {#if activeCall?.status === 6}
            <button
                type="button"
                title={localHalfDuplex ? t("call.switch_to_full_duplex") : t("call.switch_to_half_duplex")}
                class="p-2.5 rounded-full transition-all duration-200 bg-sem-surface-muted text-sem-fg-muted hover:bg-sem-surface-subtle focus-ring-sem cursor-pointer"
                onclick={() => ontoggleduplex?.()}
            >
                <MaterialDesignIcon
                    iconName={localHalfDuplex ? "access-point-network" : "swap-horizontal"}
                    class="size-5"
                />
            </button>
        {/if}
        <button
            type="button"
            title={localMicMuted ? t("call.unmute_mic") : t("call.mute_mic")}
            class="p-2.5 rounded-full transition-all duration-200 focus-ring-sem cursor-pointer {localMicMuted
                ? 'bg-sem-danger text-white shadow-lg shadow-sem-danger/30'
                : 'bg-sem-surface-muted text-sem-fg-muted hover:bg-sem-surface-subtle'}"
            onclick={() => ontogglemic?.()}
        >
            <MaterialDesignIcon iconName={localMicMuted ? "microphone-off" : "microphone"} class="size-5" />
        </button>
        <button
            type="button"
            title={localSpeakerMuted ? t("call.unmute_speaker") : t("call.mute_speaker")}
            class="p-2.5 rounded-full transition-all duration-200 focus-ring-sem cursor-pointer {localSpeakerMuted
                ? 'bg-sem-danger text-white shadow-lg shadow-sem-danger/30'
                : 'bg-sem-surface-muted text-sem-fg-muted hover:bg-sem-surface-subtle'}"
            onclick={() => ontogglespeaker?.()}
        >
            <MaterialDesignIcon iconName={localSpeakerMuted ? "volume-off" : "volume-high"} class="size-5" />
        </button>
        <button
            type="button"
            title={activeCall?.is_incoming && activeCall.status === 4 ? t("call.decline_call") : t("call.hangup_call")}
            class="p-2.5 rounded-full bg-sem-danger text-white hover:bg-sem-danger/90 shadow-lg shadow-sem-danger/30 transition-all duration-200 focus-ring-sem cursor-pointer"
            onclick={() => onhangup?.()}
        >
            <MaterialDesignIcon iconName="phone-hangup" class="size-5 rotate-135" />
        </button>
        {#if activeCall?.is_incoming && activeCall.status === 4}
            <button
                type="button"
                title={t("call.send_to_voicemail")}
                class="p-2.5 rounded-full bg-sem-accent text-white hover:bg-sem-accent/90 shadow-lg shadow-sem-accent/30 transition-all duration-200 focus-ring-sem cursor-pointer"
                onclick={() => onsendtovoicemail?.()}
            >
                <MaterialDesignIcon iconName="voicemail" class="size-5" />
            </button>
            <button
                type="button"
                title={t("call.answer_call")}
                class="p-2.5 rounded-full bg-emerald-600 text-white hover:bg-emerald-500 shadow-lg shadow-emerald-600/30 focus-ring-sem cursor-pointer"
                onclick={() => onanswer?.()}
            >
                <MaterialDesignIcon iconName="phone" class="size-5" />
            </button>
        {/if}
    </div>

    {#if activeCall?.status === 6 && localHalfDuplex && !isEnded}
        <button
            type="button"
            class="mt-3 w-full flex items-center justify-center gap-2 rounded-xl py-3 text-sm font-bold text-white select-none touch-none focus-ring-sem cursor-pointer {localPttActive
                ? 'bg-amber-500'
                : 'bg-sem-accent'}"
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
            <MaterialDesignIcon iconName="microphone" class="size-5" />
            <span>{localPttActive ? t("call.ptt_transmitting") : t("call.ptt_hold_to_talk")}</span>
        </button>
    {/if}
{/if}
