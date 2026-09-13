<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";

    interface Props {
        isLoading?: boolean;
        loadingStatus?: string;
        totalNodesToLoad?: number;
        loadedNodesCount?: number;
        currentBatch?: number;
        totalBatches?: number;
    }

    let {
        isLoading = false,
        loadingStatus = "",
        totalNodesToLoad = 0,
        loadedNodesCount = 0,
        currentBatch = 0,
        totalBatches = 0,
    }: Props = $props();

    let percent = $derived(totalNodesToLoad > 0 ? Math.round((loadedNodesCount / totalNodesToLoad) * 100) : 0);
</script>

{#if isLoading}
    <div class="absolute inset-0 z-20 flex items-center justify-center bg-zinc-950/15 transition-all duration-300">
        <div
            class="bg-white/90 dark:bg-zinc-900/90 border border-sem-border rounded-2xl px-6 py-4 flex flex-col items-center gap-3"
        >
            <div class="relative">
                <div class="w-12 h-12 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin"></div>
                <div class="absolute inset-0 flex items-center justify-center">
                    <div
                        class="w-6 h-6 border-4 border-emerald-500/20 border-b-emerald-500 rounded-full animate-spin-reverse"
                    ></div>
                </div>
            </div>
            <div class="text-sm font-medium text-sem-fg">{loadingStatus}</div>
            {#if totalNodesToLoad > 0}
                <div class="w-48 space-y-2">
                    <div class="h-1.5 bg-gray-200 dark:bg-zinc-800 rounded-full overflow-hidden">
                        <div
                            class="h-full bg-blue-500 transition-all duration-300 shadow-[0_0_8px_rgba(59,130,246,0.5)]"
                            style="width: {percent}%"
                        ></div>
                    </div>
                    {#if totalBatches > 0}
                        <div
                            class="flex justify-between items-center text-[10px] font-bold text-sem-fg-muted uppercase tracking-wider"
                        >
                            <span>{t("visualiser.batch")} {currentBatch} / {totalBatches}</span>
                            <span>{percent}%</span>
                        </div>
                    {/if}
                </div>
            {/if}
        </div>
    </div>
{/if}
