<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    interface Props {
        minZoom: number;
        maxZoom: number;
        estimatedTiles?: number | string;
        exporting?: boolean;
        tileLimitExceeded?: boolean;
        onCancel?: () => void;
        onStart?: () => void;
        onUpdateMinZoom?: (val: number) => void;
        onUpdateMaxZoom?: (val: number) => void;
    }

    let {
        minZoom,
        maxZoom,
        estimatedTiles = 0,
        exporting = false,
        tileLimitExceeded = false,
        onCancel,
        onStart,
        onUpdateMinZoom,
        onUpdateMaxZoom,
    }: Props = $props();
</script>

<div
    class="absolute top-0 mt-14 left-1/2 -translate-x-1/2 z-20 w-80 bg-sem-surface rounded-xl shadow-2xl border border-sem-border overflow-hidden text-sem-fg"
>
    <div class="p-4 border-b border-sem-border flex items-center justify-between">
        <h3 class="font-semibold text-sem-fg">{t("map.export_area")}</h3>
        <button
            class="text-gray-500 hover:text-gray-700 dark:hover:text-zinc-300 cursor-pointer"
            onclick={() => onCancel?.()}
        >
            <MaterialDesignIcon iconName="close" class="size-5" />
        </button>
    </div>
    <div class="p-4 space-y-4">
        <div class="grid grid-cols-2 gap-4">
            <div>
                <label class="block text-xs font-bold text-gray-500 uppercase mb-1" for="export-min-zoom"
                    >{t("map.min_zoom")}</label
                >
                <input
                    id="export-min-zoom"
                    value={minZoom}
                    type="number"
                    min="0"
                    max="20"
                    class="w-full bg-gray-50 dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-lg px-3 py-2 text-sm text-sem-fg"
                    oninput={(e) => onUpdateMinZoom?.(Number((e.target as HTMLInputElement).value))}
                />
            </div>
            <div>
                <label class="block text-xs font-bold text-gray-500 uppercase mb-1" for="export-max-zoom"
                    >{t("map.max_zoom")}</label
                >
                <input
                    id="export-max-zoom"
                    value={maxZoom}
                    type="number"
                    min="0"
                    max="20"
                    class="w-full bg-gray-50 dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-lg px-3 py-2 text-sm text-sem-fg"
                    oninput={(e) => onUpdateMaxZoom?.(Number((e.target as HTMLInputElement).value))}
                />
            </div>
        </div>
        <div class="flex justify-between items-center text-sm">
            <span class="text-sem-fg-muted">{t("map.tile_count")}:</span>
            <span class="font-bold text-blue-600">{estimatedTiles}</span>
        </div>
        {#if tileLimitExceeded}
            <p class="text-xs text-red-600 dark:text-red-400 font-semibold">
                {t("map.export_tile_limit_exceeded")}
            </p>
        {/if}
        <div class="flex gap-2">
            <button
                type="button"
                disabled={exporting}
                class="flex-1 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-zinc-700 dark:hover:bg-zinc-600 disabled:bg-gray-100 dark:disabled:bg-zinc-800 text-sem-fg rounded-lg font-bold transition-colors cursor-pointer"
                onclick={() => onCancel?.()}
            >
                {t("common.cancel")}
            </button>
            <button
                type="button"
                disabled={exporting || tileLimitExceeded}
                class="flex-1 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white rounded-lg font-bold transition-colors shadow-md cursor-pointer"
                onclick={() => onStart?.()}
            >
                {t("map.start_export")}
            </button>
        </div>
    </div>
</div>
