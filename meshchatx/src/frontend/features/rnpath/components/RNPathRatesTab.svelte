<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { calculateRate, formatTimeAgo } from "../lib/pathQuery.js";
    import type { RateEntry } from "../lib/types.js";

    let {
        rateTable = [],
    }: {
        rateTable?: RateEntry[];
    } = $props();
</script>

<div class="space-y-4">
    {#if rateTable.length === 0}
        <div class="rounded-lg border border-sem-border bg-sem-surface p-8 sm:p-12 text-center text-gray-500">
            No announce rate data available.
        </div>
    {:else}
        <div class="grid gap-4">
            {#each rateTable as rate (rate.hash)}
                <div class="rounded-lg border border-sem-border bg-sem-surface p-3 sm:p-4">
                    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
                        <span class="font-mono text-sm font-bold text-indigo-600 dark:text-indigo-400 truncate">
                            {rate.hash}
                        </span>
                        {#if rate.blocked_until > Date.now() / 1000}
                            <span
                                class="px-2 py-0.5 text-[10px] font-bold bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-sm"
                            >
                                RATE LIMITED
                            </span>
                        {/if}
                    </div>
                    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
                        <div>
                            <div class="text-[10px] uppercase text-gray-500">Last Heard</div>
                            <div class="text-xs font-medium">{formatTimeAgo(rate.last)}</div>
                        </div>
                        <div>
                            <div class="text-[10px] uppercase text-gray-500">Announces</div>
                            <div class="text-xs font-medium">{rate.timestamps ? rate.timestamps.length : 0}</div>
                        </div>
                        <div>
                            <div class="text-[10px] uppercase text-gray-500">Violations</div>
                            <div class="text-xs font-medium {rate.rate_violations > 0 ? 'text-red-500' : ''}">
                                {rate.rate_violations}
                            </div>
                        </div>
                        <div>
                            <div class="text-[10px] uppercase text-gray-500">Rate</div>
                            <div class="text-xs font-medium">{calculateRate(rate)} / hr</div>
                        </div>
                    </div>
                </div>
            {/each}
        </div>
    {/if}
</div>
