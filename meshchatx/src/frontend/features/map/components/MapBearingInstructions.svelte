<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";

    interface Props {
        fromGpsActive?: boolean;
        awaitingSecondTap?: boolean;
        onusemylocation?: () => void;
    }

    let { fromGpsActive = false, awaitingSecondTap = false, onusemylocation }: Props = $props();

    let instructionText = $derived.by(() => {
        if (fromGpsActive) {
            return t("map.bearing_hint_destination");
        }
        if (awaitingSecondTap) {
            return t("map.bearing_hint_second");
        }
        return t("map.bearing_hint_first");
    });

    let showFromHere = $derived(!fromGpsActive);
</script>

<div
    class="absolute top-[calc(0.5rem+2.75rem+0.5rem+2.75rem)] left-1/2 -translate-x-1/2 z-19 w-[min(100vw-2rem,24rem)] pointer-events-auto"
>
    <div
        class="bg-white/95 dark:bg-zinc-900/95 backdrop-blur-sm border border-sem-border rounded-xl shadow-lg px-3 py-2 text-xs text-sem-fg"
    >
        <p class="font-medium text-center {showFromHere ? 'mb-2' : ''}">{instructionText}</p>
        {#if showFromHere}
            <button
                type="button"
                class="w-full py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-semibold transition-colors"
                onclick={() => onusemylocation?.()}
            >
                {t("map.bearing_from_here")}
            </button>
        {/if}
    </div>
</div>
