<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { formatLastAnnounced, formatMeshUptime } from "../lib/pageNodesFormat.js";
    import type { PageNode } from "../lib/types.js";

    interface Props {
        node: PageNode;
        isSelected?: boolean;
        onSelect: (node: PageNode) => void;
        onStart: (nodeId: string) => void;
        onStop: (nodeId: string) => void;
        onAnnounce: (nodeId: string) => void;
        onView: (node: PageNode) => void;
        onDelete: (nodeId: string) => void;
    }

    let { node, isSelected = false, onSelect, onStart, onStop, onAnnounce, onView, onDelete }: Props = $props();

    function handleRowKeydown(event: KeyboardEvent) {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            onSelect(node);
        }
    }
</script>

<div
    class="py-3 sm:py-4 space-y-2 cursor-pointer hover:bg-black/5 dark:hover:bg-white/5 transition-colors rounded-lg -mx-3 sm:-mx-4 px-3 sm:px-4 {isSelected
        ? 'bg-black/5 dark:bg-white/5'
        : ''}"
    onclick={() => onSelect(node)}
    onkeydown={handleRowKeydown}
    role="button"
    tabindex="0"
>
    <div class="flex items-center justify-between gap-3">
        <div class="flex items-center gap-3 min-w-0">
            <div class="w-3 h-3 rounded-full shrink-0 {node.running ? 'bg-green-500' : 'bg-gray-400'}"></div>
            <div class="min-w-0">
                <div class="flex items-center gap-2">
                    <div class="font-semibold text-sem-fg truncate">
                        {node.name}
                    </div>
                    {#if !node.announce_enabled}
                        <span
                            class="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 shrink-0"
                        >
                            {t("tools.mesh_server.announce_off_badge")}
                        </span>
                    {/if}
                </div>
                {#if node.destination_hash}
                    <div class="text-xs font-mono text-sem-fg-muted truncate">
                        {node.destination_hash}
                    </div>
                {/if}
            </div>
        </div>
        <div class="flex items-center gap-1.5 shrink-0 flex-wrap justify-end">
            <span class="text-xs text-sem-fg-muted mr-1">
                {t("tools.mesh_server.stats_pages_files", {
                    pages: node.pages.length,
                    files: node.files.length,
                })}
            </span>
            {#if !node.running}
                <button
                    type="button"
                    class="primary-chip focus-ring-sem py-1! px-2.5! text-xs!"
                    onclick={(e) => {
                        e.stopPropagation();
                        onStart(node.node_id);
                    }}
                >
                    {t("tools.mesh_server.start")}
                </button>
            {:else}
                <button
                    type="button"
                    class="secondary-chip focus-ring-sem py-1! px-2.5! text-xs! text-red-500! hover:bg-red-50! dark:hover:bg-red-900/20!"
                    onclick={(e) => {
                        e.stopPropagation();
                        onStop(node.node_id);
                    }}
                >
                    {t("tools.mesh_server.stop")}
                </button>
            {/if}
            {#if node.running}
                <button
                    type="button"
                    class="secondary-chip focus-ring-sem py-1! px-2.5! text-xs!"
                    onclick={(e) => {
                        e.stopPropagation();
                        onAnnounce(node.node_id);
                    }}
                >
                    {t("tools.mesh_server.announce")}
                </button>
            {/if}
            {#if node.running && node.destination_hash}
                <button
                    type="button"
                    class="secondary-chip focus-ring-sem py-1! px-2.5! text-xs!"
                    onclick={(e) => {
                        e.stopPropagation();
                        onView(node);
                    }}
                >
                    <MaterialDesignIcon iconName="eye" class="w-3.5 h-3.5" />
                    {t("tools.mesh_server.view")}
                </button>
            {/if}
            <button
                type="button"
                class="secondary-chip focus-ring-sem py-1! px-2.5! text-xs! text-red-500! hover:bg-red-50! dark:hover:bg-red-900/20!"
                onclick={(e) => {
                    e.stopPropagation();
                    onDelete(node.node_id);
                }}
            >
                <MaterialDesignIcon iconName="delete" class="w-3.5 h-3.5" />
            </button>
        </div>
    </div>

    {#if node.stats || node.running}
        <div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-sem-fg-muted pl-6">
            {#if node.running}
                <span>
                    {t("tools.mesh_server.uptime", {
                        time: formatMeshUptime(node.uptime_seconds),
                    })}
                </span>
            {/if}
            <span>
                {t("tools.mesh_server.connections", {
                    count: node.unique_connections ?? 0,
                })}
            </span>
            {#if node.stats}
                <span>
                    {t("tools.mesh_server.pages_served", {
                        count: node.stats.pages_served,
                    })}
                </span>
                <span>
                    {t("tools.mesh_server.files_served", {
                        count: node.stats.files_served,
                    })}
                </span>
                <span>
                    {t("tools.mesh_server.links", {
                        count: node.stats.links_established,
                    })}
                </span>
            {/if}
            <span>{formatLastAnnounced(node.last_announced_at)}</span>
        </div>
    {/if}
</div>
