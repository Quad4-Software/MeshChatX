<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import { highlightMatch } from "../lib/docsToc.js";
    import type { SearchResultItem } from "../lib/types.js";

    interface Props {
        searchQuery: string;
        searchResults: SearchResultItem[];
        isSearching: boolean;
        searchError: string | null;
        onNavigate: (path: string) => void;
        onClearSearch: () => void;
    }

    let { searchQuery, searchResults, isSearching, searchError, onNavigate, onClearSearch }: Props = $props();
</script>

{#if searchResults.length > 0 && searchQuery}
    <div class="absolute inset-0 z-20 bg-sem-surface overflow-y-auto">
        <div class="max-w-2xl mx-auto p-6 space-y-6">
            <div class="flex items-center justify-between px-2">
                <h2 class="text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                    {t("docs.search_results")}
                </h2>
                <span class="text-[10px] font-bold text-blue-500 px-2 py-0.5 bg-sem-surface-muted rounded-full">
                    {t("docs.matches_count", { count: searchResults.length })}
                </span>
            </div>
            <div class="space-y-2">
                {#each searchResults as result (result.path)}
                    <button
                        type="button"
                        class="w-full text-left group p-4 hover:bg-sem-surface-muted/50 rounded-2xl cursor-pointer transition-colors border border-sem-border/50 hover:border-blue-200 dark:hover:border-blue-900/30"
                        onclick={() => onNavigate(result.path)}
                    >
                        <div class="flex items-start justify-between gap-4">
                            <div
                                class="font-bold text-sm text-sem-fg group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors"
                            >
                                {result.title}
                            </div>
                            <div class="flex items-center space-x-2">
                                <span
                                    class="px-1.5 py-0.5 rounded-sm bg-sem-surface-muted text-[8px] font-bold text-gray-500 uppercase tracking-tighter"
                                >
                                    {result.source}
                                </span>
                                <div class="text-[9px] text-gray-400 uppercase font-mono mt-0.5 shrink-0">
                                    {result.path.split("/").pop()}
                                </div>
                            </div>
                        </div>
                        <p class="mt-1.5 text-xs text-sem-fg-muted line-clamp-3 leading-relaxed">
                            <!-- eslint-disable-next-line svelte/no-at-html-tags -- sanitized highlight markup -->
                            {@html highlightMatch(result.snippet, searchQuery)}
                        </p>
                    </button>
                {/each}
            </div>
        </div>
    </div>
{/if}

{#if searchQuery && !isSearching && searchResults.length === 0 && !searchError}
    <div class="absolute inset-0 z-20 bg-sem-surface flex flex-col items-center justify-center p-8 text-center">
        <div class="w-16 h-16 bg-gray-50 dark:bg-zinc-800/50 rounded-full flex items-center justify-center mb-4">
            <MaterialDesignIcon iconName="text-search" class="w-8 h-8 text-gray-300 dark:text-zinc-600" />
        </div>
        <h3 class="text-sm font-medium text-sem-fg">{t("docs.no_results")}</h3>
        <p class="text-xs text-sem-fg-muted mt-1">{t("docs.no_results_hint")}</p>
        <button
            type="button"
            class="mt-4 text-xs font-bold text-blue-500 hover:text-blue-600 transition-colors"
            onclick={onClearSearch}
        >
            {t("docs.clear_search")}
        </button>
    </div>
{/if}

{#if searchError && searchQuery}
    <div class="absolute inset-0 z-20 bg-sem-surface flex flex-col items-center justify-center p-8 text-center">
        <div class="w-16 h-16 bg-red-50 dark:bg-red-950/30 rounded-full flex items-center justify-center mb-4">
            <MaterialDesignIcon iconName="alert-circle-outline" class="w-8 h-8 text-red-400" />
        </div>
        <h3 class="text-sm font-medium text-sem-fg">{t("docs.search_failed")}</h3>
        <p class="text-xs text-sem-fg-muted mt-1 max-w-sm">{searchError}</p>
        <button
            type="button"
            class="mt-4 text-xs font-bold text-blue-500 hover:text-blue-600 transition-colors"
            onclick={onClearSearch}
        >
            {t("docs.clear_search")}
        </button>
    </div>
{/if}
