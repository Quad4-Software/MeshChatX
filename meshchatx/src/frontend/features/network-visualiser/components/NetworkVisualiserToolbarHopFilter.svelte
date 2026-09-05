<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import { HOP_SLIDER_POS_ALL, hopSliderPosToMaxHops, hopMaxHopsToSliderPos } from "../lib/hopMaxFilterSliderMap.js";

    interface Props {
        hopMaxFilter?: number | null;
        onupdatehopmaxfilter?: (val: number | null) => void;
    }

    let { hopMaxFilter = 4, onupdatehopmaxfilter }: Props = $props();

    let hopMaxInputDraft = $state<string | null>(null);

    let hopSliderUiPos = $derived(hopMaxHopsToSliderPos(hopMaxFilter));
    let hopMaxInputShown = $derived(
        hopMaxInputDraft !== null ? hopMaxInputDraft : hopMaxFilter === null ? "" : String(hopMaxFilter)
    );
    let hopSliderAriaText = $derived(hopMaxFilter === null ? t("visualiser.all") : String(hopMaxFilter));

    function onHopSliderInput(e: Event) {
        const target = e.target as HTMLInputElement;
        const v = hopSliderPosToMaxHops(Number(target.value));
        onupdatehopmaxfilter?.(v);
    }

    function onHopMaxInputFocus() {
        hopMaxInputDraft = hopMaxFilter === null ? "" : String(hopMaxFilter);
    }

    function onHopMaxInputInput(e: Event) {
        const target = e.target as HTMLInputElement;
        const raw = target.value.replace(/\D/g, "");
        hopMaxInputDraft = raw;
        if (raw === "") return;
        const n = parseInt(raw, 10);
        if (!Number.isFinite(n)) return;
        const clamped = Math.max(0, Math.min(128, Math.round(n)));
        onupdatehopmaxfilter?.(clamped);
        hopMaxInputDraft = String(clamped);
    }

    function onHopMaxInputBlur() {
        const d = hopMaxInputDraft;
        hopMaxInputDraft = null;
        if (d === null) return;
        const trimmed = (d || "").trim();
        if (trimmed === "") {
            onupdatehopmaxfilter?.(null);
            return;
        }
        const n = parseInt(trimmed, 10);
        if (!Number.isFinite(n)) return;
        onupdatehopmaxfilter?.(Math.max(0, Math.min(128, Math.round(n))));
    }
</script>

<div class="space-y-2">
    <div class="flex items-center justify-between gap-2">
        <label for="hop-filter-slider" class="text-sm font-semibold text-sem-fg-muted cursor-pointer">
            {t("visualiser.max_hops_filter")}
        </label>
        <input
            id="hop-max-hops-input"
            type="text"
            inputmode="numeric"
            autocomplete="off"
            maxlength="4"
            aria-label={t("visualiser.max_hops_filter")}
            class="w-13 shrink-0 rounded-lg border border-gray-200 bg-white px-1.5 py-1 text-center text-xs font-bold text-blue-600 tabular-nums shadow-xs focus:border-blue-500 focus:outline-hidden focus:ring-1 focus:ring-blue-500/40 dark:border-zinc-600 dark:bg-zinc-800 dark:text-blue-400 dark:focus:border-blue-500"
            value={hopMaxInputShown}
            placeholder={t("visualiser.all")}
            onfocus={onHopMaxInputFocus}
            oninput={onHopMaxInputInput}
            onblur={onHopMaxInputBlur}
        />
    </div>
    <input
        id="hop-filter-slider"
        type="range"
        min="0"
        max={HOP_SLIDER_POS_ALL}
        step="1"
        value={hopSliderUiPos}
        aria-valuetext={hopSliderAriaText}
        class="w-full h-2 rounded-lg appearance-none cursor-pointer bg-gray-200 dark:bg-zinc-700 accent-blue-600 dark:accent-blue-500"
        oninput={onHopSliderInput}
    />
</div>
