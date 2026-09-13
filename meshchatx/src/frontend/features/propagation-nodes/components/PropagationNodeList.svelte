<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import { formatDestinationHash, formatPathLabel, formatTimeAgo } from "../lib/propagationFormat.js";
    import type { NodePathInfo, PropagationNodeItem, PropagationSortBy } from "../lib/types.js";

    interface Props {
        totalNodesCount: number;
        filteredNodesCount: number;
        paginatedNodes: PropagationNodeItem[];
        preferredHash: string | null | undefined;
        searchTerm: string;
        sortBy: PropagationSortBy;
        currentPage: number;
        totalPages: number;
        startIndex: number;
        endIndex: number;
        nodePathsByHash: Record<string, NodePathInfo | null>;
        onSelectPreferredNode: (hash: string) => void;
        onRequestPath: (hash: string) => void;
        onPageChange: (page: number) => void;
        onReloadNodes: () => void;
    }

    let {
        totalNodesCount,
        filteredNodesCount,
        paginatedNodes,
        preferredHash,
        searchTerm = $bindable(),
        sortBy = $bindable(),
        currentPage,
        totalPages,
        startIndex,
        endIndex,
        nodePathsByHash,
        onSelectPreferredNode,
        onRequestPath,
        onPageChange,
        onReloadNodes,
    }: Props = $props();

    function isPreferred(hash: string): boolean {
        return preferredHash === hash;
    }
</script>

{#if totalNodesCount > 0}
    <div class="shrink-0 flex items-center gap-2 px-3 py-2 border-b border-sem-border">
        <div class="relative min-w-0 flex-1">
            <MaterialDesignIcon
                iconName="magnify"
                class="absolute left-3 top-1/2 -translate-y-1/2 size-5 text-sem-fg-muted pointer-events-none"
            />
            <input
                bind:value={searchTerm}
                type="search"
                data-testid="prop-nodes-search"
                placeholder={t("tools.propagation_nodes.search_placeholder", { count: totalNodesCount })}
                class="input-field pl-11! py-2 text-sm"
            />
        </div>
        <select
            bind:value={sortBy}
            data-testid="prop-nodes-sort"
            class="shrink-0 w-44 bg-sem-surface-muted border border-sem-border text-sm rounded-2xl px-2.5 py-2 text-sem-fg"
        >
            <option value="preferred">{t("tools.propagation_nodes.sort_preferred")}</option>
            <option value="recent">{t("tools.propagation_nodes.sort_recent")}</option>
            <option value="oldest">{t("tools.propagation_nodes.sort_oldest")}</option>
            <option value="name">{t("tools.propagation_nodes.sort_name")}</option>
            <option value="name-desc">{t("tools.propagation_nodes.sort_name_desc")}</option>
        </select>
    </div>
{/if}

<div data-testid="prop-nodes-list" class="flex-1 min-h-0 overflow-y-auto">
    {#if paginatedNodes.length > 0}
        <div
            class="divide-y divide-sem-border"
            role="radiogroup"
            aria-label={t("tools.propagation_nodes.preferred_heading")}
        >
            {#each paginatedNodes as propagationNode (propagationNode.destination_hash)}
                <div
                    class="flex items-center gap-0.5 hover:bg-sem-surface-muted/60 {isPreferred(
                        propagationNode.destination_hash
                    )
                        ? 'bg-blue-50/70 dark:bg-blue-950/20'
                        : ''}"
                >
                    <button
                        type="button"
                        role="radio"
                        aria-checked={isPreferred(propagationNode.destination_hash)}
                        data-testid={"prop-node-" + propagationNode.destination_hash}
                        class="flex min-w-0 flex-1 items-center gap-2.5 px-3 py-2 text-left"
                        title={isPreferred(propagationNode.destination_hash)
                            ? t("tools.propagation_nodes.preferred_badge")
                            : t("tools.propagation_nodes.set_as_preferred")}
                        onclick={() => onSelectPreferredNode(propagationNode.destination_hash)}
                    >
                        <MaterialDesignIcon
                            iconName={isPreferred(propagationNode.destination_hash)
                                ? "radiobox-marked"
                                : "radiobox-blank"}
                            class="size-5 shrink-0 {isPreferred(propagationNode.destination_hash)
                                ? 'text-sem-accent'
                                : 'text-sem-fg-muted'}"
                        />
                        <div class="min-w-0 flex-1">
                            <div class="flex items-center gap-1.5 min-w-0">
                                <span class="truncate text-sm font-medium">
                                    {propagationNode.operator_display_name ||
                                        t("tools.propagation_nodes.unknown_operator")}
                                </span>
                                {#if propagationNode.is_propagation_enabled === false}
                                    <span
                                        class="shrink-0 rounded-full bg-red-100 dark:bg-red-900/30 px-1.5 text-[10px] font-semibold text-red-700 dark:text-red-300"
                                    >
                                        {t("tools.propagation_nodes.disabled")}
                                    </span>
                                {/if}
                                {#if propagationNode.is_local_node}
                                    <span
                                        class="shrink-0 rounded-full bg-emerald-100 dark:bg-emerald-900/30 px-1.5 text-[10px] font-semibold text-emerald-700 dark:text-emerald-300"
                                    >
                                        {t("tools.propagation_nodes.our_node")}
                                    </span>
                                {/if}
                            </div>
                            <div
                                class="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-sem-fg-muted"
                            >
                                <span class="font-mono truncate" title={propagationNode.destination_hash}>
                                    {formatDestinationHash(propagationNode.destination_hash)}
                                </span>
                                <span>
                                    {t("tools.propagation_nodes.announced_ago", {
                                        time: formatTimeAgo(propagationNode.updated_at),
                                    })}
                                </span>
                                <span>
                                    {formatPathLabel(nodePathsByHash[propagationNode.destination_hash])}
                                </span>
                            </div>
                        </div>
                    </button>
                    <button
                        type="button"
                        class="inline-flex size-8 shrink-0 items-center justify-center rounded-lg mr-2 text-sem-fg-muted hover:bg-sem-surface-muted hover:text-sem-accent"
                        title={t("tools.propagation_nodes.find_path")}
                        onclick={() => onRequestPath(propagationNode.destination_hash)}
                    >
                        <MaterialDesignIcon iconName="map-marker-path" class="size-4" />
                    </button>
                </div>
            {/each}
        </div>
    {/if}

    {#if totalPages > 1}
        <div
            class="flex items-center justify-between gap-2 px-3 py-2 border-t border-sem-border text-xs text-sem-fg-muted"
        >
            <span>
                {t("tools.propagation_nodes.showing_range", {
                    start: startIndex + 1,
                    end: endIndex,
                    total: filteredNodesCount,
                })}
            </span>
            <div class="flex items-center gap-1">
                <button
                    disabled={currentPage === 1}
                    type="button"
                    class="secondary-chip text-xs px-2 py-1 disabled:opacity-40"
                    onclick={() => onPageChange(Math.max(1, currentPage - 1))}
                >
                    {t("tools.propagation_nodes.previous")}
                </button>
                <button
                    disabled={currentPage === totalPages}
                    type="button"
                    class="secondary-chip text-xs px-2 py-1 disabled:opacity-40"
                    onclick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
                >
                    {t("tools.propagation_nodes.next")}
                </button>
            </div>
        </div>
    {/if}

    {#if filteredNodesCount === 0}
        <div class="flex h-full min-h-40 items-center justify-center px-4 text-center">
            {#if totalNodesCount === 0}
                <div class="flex flex-col items-center text-sem-fg-muted">
                    <MaterialDesignIcon iconName="mailbox" class="size-8 mb-2 opacity-70" />
                    <div class="font-semibold text-sem-fg">{t("tools.propagation_nodes.no_nodes_title")}</div>
                    <div class="text-sm mt-1">{t("tools.propagation_nodes.empty_announced")}</div>
                    <button type="button" class="primary-chip mt-3 text-xs" onclick={onReloadNodes}>
                        {t("tools.propagation_nodes.reload")}
                    </button>
                </div>
            {:else if searchTerm !== ""}
                <div class="flex flex-col items-center text-sem-fg-muted">
                    <MaterialDesignIcon iconName="magnify" class="size-8 mb-2 opacity-70" />
                    <div class="font-semibold text-sem-fg">{t("tools.propagation_nodes.no_search_title")}</div>
                    <div class="text-sm mt-1">{t("tools.propagation_nodes.no_search_hint")}</div>
                </div>
            {/if}
        </div>
    {/if}
</div>
