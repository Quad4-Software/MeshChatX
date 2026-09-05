<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    interface Props {
        show?: boolean;
        hasOfflineMap?: boolean;
        onretry?: () => void;
        onswitchoffline?: () => void;
        ondismiss?: () => void;
        onopensettings?: () => void;
    }

    let { show = false, hasOfflineMap = false, onretry, onswitchoffline, ondismiss, onopensettings }: Props = $props();
</script>

{#if show}
    <div class="absolute inset-x-4 top-16 z-35 max-w-lg mx-auto pointer-events-auto">
        <div
            class="flex items-start gap-3 p-4 rounded-xl shadow-2xl border border-amber-500/40 bg-zinc-900/95 backdrop-blur-md text-zinc-100"
            role="status"
        >
            <MaterialDesignIcon iconName="wifi-off" class="size-6 shrink-0 mt-0.5 text-amber-400" />
            <div class="flex-1 min-w-0 space-y-2">
                <p class="text-sm font-semibold leading-snug text-white">
                    {t("map.tile_connectivity_title")}
                </p>
                <p class="text-xs leading-relaxed text-zinc-300">
                    {t("map.tile_connectivity_body")}
                </p>
                <div class="flex flex-wrap gap-2 pt-1">
                    <button
                        type="button"
                        class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white transition-colors cursor-pointer"
                        onclick={() => onretry?.()}
                    >
                        {t("map.tile_connectivity_retry")}
                    </button>
                    {#if hasOfflineMap}
                        <button
                            type="button"
                            class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-zinc-700 hover:bg-zinc-600 text-white transition-colors cursor-pointer"
                            onclick={() => onswitchoffline?.()}
                        >
                            {t("map.tile_connectivity_use_offline")}
                        </button>
                    {/if}
                    <button
                        type="button"
                        class="px-3 py-1.5 rounded-lg text-xs font-semibold text-zinc-300 hover:bg-zinc-800 transition-colors cursor-pointer"
                        onclick={() => ondismiss?.()}
                    >
                        {t("map.tile_connectivity_dismiss")}
                    </button>
                    <button
                        type="button"
                        class="px-3 py-1.5 rounded-lg text-xs font-semibold text-zinc-400 hover:text-zinc-200 transition-colors cursor-pointer"
                        onclick={() => onopensettings?.()}
                    >
                        {t("map.settings")}
                    </button>
                </div>
            </div>
        </div>
    </div>
{/if}
