<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { tick } from "svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import ToastUtils from "../../../js/ToastUtils.js";
    import GlobalState from "../../../js/GlobalState.js";
    import { clampFloatingToViewport } from "../../../js/clampFloatingToViewport.js";
    import { computeCaret, type ContextMenuCaret } from "../../../js/contextMenuCaret.js";
    import { t } from "../../../js/i18n.js";
    import { loadNomadAnnouncesSort, saveNomadAnnouncesSort } from "../../../js/browserLayoutStore.js";
    import NomadAnnounceRow from "./NomadAnnounceRow.svelte";
    import NomadAnnounceContextMenu from "./NomadAnnounceContextMenu.svelte";
    import { bulkBlockNodeDestinations } from "../lib/nomadSidebarActions.js";
    import { sortAnnouncesNodes } from "../lib/nomadAnnouncesSort.js";
    import type { NomadFavourite, NomadNode } from "../lib/types.js";

    interface Props {
        nodes: Record<string, NomadNode>;
        favourites: NomadFavourite[];
        selectedDestinationHash?: string;
        nodesSearchTerm?: string;
        totalNodesCount?: number;
        isLoadingMoreNodes?: boolean;
        isSearchingNodes?: boolean;
        hasMoreNodes?: boolean;
        onnodeclick?: (node: NomadNode) => void;
        onaddfavourite?: (node: NomadNode) => void;
        onnodessearchchanged?: (term: string) => void;
        onloadmorenodes?: () => void;
        onbulkaddfavourites?: (nodes: NomadNode[]) => void;
    }

    let {
        nodes = {},
        favourites = [],
        selectedDestinationHash = "",
        nodesSearchTerm = "",
        totalNodesCount = 0,
        isLoadingMoreNodes = false,
        isSearchingNodes = false,
        hasMoreNodes = false,
        onnodeclick,
        onaddfavourite,
        onnodessearchchanged,
        onloadmorenodes,
        onbulkaddfavourites,
    }: Props = $props();

    let selectionMode = $state(false);
    let selectedHashes = $state<string[]>([]);
    let contextMenu = $state({
        show: false,
        x: 0,
        y: 0,
        node: null as NomadNode | null,
        justOpened: false,
    });
    let activeDropdownHash = $state<string | null>(null);

    let menuPanel = $state<HTMLDivElement | null>(null);
    let menuLeft = $state(0);
    let menuTop = $state(0);
    let menuCaret: ContextMenuCaret | null = $state(null);

    let announcesSort = $state(loadNomadAnnouncesSort());

    function onAnnouncesSortChange(e: Event) {
        announcesSort = (e.target as HTMLSelectElement).value;
        saveNomadAnnouncesSort(announcesSort);
    }

    const orderedNodes = $derived(sortAnnouncesNodes(nodes, announcesSort));

    const searchedNodes = $derived.by(() => {
        const s = (nodesSearchTerm || "").toLowerCase().trim();
        if (!s) return orderedNodes;
        return orderedNodes.filter((n) => {
            const name = (n.custom_display_name || n.display_name || "").toLowerCase();
            const hash = (n.destination_hash || "").toLowerCase();
            return name.includes(s) || hash.includes(s);
        });
    });

    const selectedHashSet = $derived(new Set(selectedHashes));
    const favouriteHashSet = $derived(new Set(favourites.map((f) => f.destination_hash)));
    const blockedHashSet = $derived(
        new Set(
            ((GlobalState.blockedDestinations || []) as Array<{ destination_hash?: string }>)
                .map((b) => b.destination_hash)
                .filter((h): h is string => Boolean(h))
        )
    );

    const flatVisibleHashes = $derived(searchedNodes.map((n) => n.destination_hash));
    const flatVisibleHashSet = $derived(new Set(flatVisibleHashes));
    const allVisibleSelected = $derived(
        flatVisibleHashes.length > 0 && flatVisibleHashes.every((h) => selectedHashSet.has(h))
    );

    function isBlocked(hash?: string): boolean {
        return Boolean(hash) && blockedHashSet.has(hash as string);
    }

    function isFavourite(hash?: string): boolean {
        return Boolean(hash) && favouriteHashSet.has(hash as string);
    }

    function toggleSelectAll() {
        if (allVisibleSelected) {
            selectedHashes = selectedHashes.filter((h) => !flatVisibleHashSet.has(h));
        } else {
            selectedHashes = [...new Set([...selectedHashes, ...flatVisibleHashes])];
        }
    }

    function toggleSelect(hash: string) {
        if (selectedHashSet.has(hash)) {
            selectedHashes = selectedHashes.filter((h) => h !== hash);
        } else {
            selectedHashes = [...selectedHashes, hash];
        }
    }

    function bulkAddFavourites() {
        const targetNodes = selectedHashes
            .map((h) => nodes[h])
            .filter((n): n is NomadNode => Boolean(n) && !isFavourite(n.destination_hash));
        if (targetNodes.length === 0) {
            ToastUtils.info(t("nomadnet.bulk_nothing_to_add_favourites"));
            return;
        }
        onbulkaddfavourites?.(targetNodes);
        selectionMode = false;
        selectedHashes = [];
    }

    async function bulkBlockNodes() {
        const targetNodes = selectedHashes
            .map((h) => nodes[h])
            .filter((n): n is NomadNode => Boolean(n) && !isBlocked(n.identity_hash) && !isBlocked(n.destination_hash));
        const ok = await bulkBlockNodeDestinations(targetNodes);
        if (ok) {
            selectionMode = false;
            selectedHashes = [];
        }
    }

    function openContextMenu(e: MouseEvent, node: NomadNode) {
        contextMenu = {
            show: true,
            justOpened: true,
            x: e.clientX,
            y: e.clientY,
            node,
        };
        activeDropdownHash = null;
        menuCaret = null;
        tick().then(() => {
            if (menuPanel) {
                const rect = menuPanel.getBoundingClientRect();
                const res = clampFloatingToViewport(e.clientX, e.clientY, rect.width, rect.height);
                menuLeft = res.left;
                menuTop = res.top;
                menuCaret = computeCaret(e.clientX, e.clientY, res.left, res.top, rect.width, rect.height);
            }
        });
        setTimeout(() => {
            contextMenu.justOpened = false;
        }, 50);
    }

    function closeContextMenu() {
        contextMenu.show = false;
        activeDropdownHash = null;
        menuCaret = null;
    }

    function handleScroll(e: Event) {
        const el = e.target as HTMLElement;
        if (el.scrollHeight - el.scrollTop - el.clientHeight < 200) {
            if (hasMoreNodes && !isLoadingMoreNodes) {
                onloadmorenodes?.();
            }
        }
    }
</script>

<svelte:window
    onclick={() => {
        if (!contextMenu.justOpened) closeContextMenu();
    }}
/>

<div class="flex-1 flex flex-col min-h-0">
    <div class="p-3 border-b border-sem-border space-y-2">
        <div class="flex gap-1.5 items-center">
            <div class="relative flex-1 min-w-0">
                <input
                    value={nodesSearchTerm}
                    type="text"
                    placeholder={t("nomadnet.search_placeholder_announces", { count: totalNodesCount })}
                    class="input-field w-full min-w-0 {isSearchingNodes ? 'pr-7' : ''}"
                    oninput={(e) => onnodessearchchanged?.((e.target as HTMLInputElement).value)}
                />
                {#if isSearchingNodes}
                    <span
                        class="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none text-gray-400"
                        title={t("nomadnet.searching_announces")}
                    >
                        <MaterialDesignIcon iconName="loading" class="size-4 animate-spin" />
                    </span>
                {/if}
            </div>
            <button
                type="button"
                class="shrink-0 self-center inline-flex items-center justify-center p-0.5 rounded-sm text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 transition-colors leading-none"
                title={t("nomadnet.sidebar_selection_mode")}
                class:text-blue-500={selectionMode}
                onclick={() => {
                    selectionMode = !selectionMode;
                    if (!selectionMode) selectedHashes = [];
                }}
            >
                <span class="block size-[14px]">
                    <MaterialDesignIcon iconName="checkbox-multiple-marked-outline" />
                </span>
            </button>
        </div>
        <select
            value={announcesSort}
            class="input-field w-full min-w-0 rounded-none text-[11px] leading-tight py-0.5 px-2"
            title={t("nomadnet.sort_announces")}
            onchange={onAnnouncesSortChange}
        >
            <option value="last_announced">{t("nomadnet.sort_last_announced")}</option>
            <option value="newest_discovered">{t("nomadnet.sort_newest_discovered")}</option>
            <option value="most_announced">{t("nomadnet.sort_most_announced")}</option>
            <option value="name">{t("nomadnet.sort_name")}</option>
        </select>

        {#if selectionMode}
            <div class="flex flex-col gap-2 px-2 py-2 bg-blue-50 dark:bg-blue-900/10 rounded-lg">
                <div class="flex items-center gap-2 min-w-0 w-full">
                    <div class="flex items-center gap-2 min-w-0 flex-1 overflow-hidden">
                        <input
                            type="checkbox"
                            checked={allVisibleSelected}
                            class="rounded-sm border-gray-300 text-blue-600 focus:ring-blue-500 shrink-0"
                            onchange={toggleSelectAll}
                        />
                        <span class="text-xs font-semibold text-blue-700 dark:text-blue-400 truncate leading-none">
                            {t("nomadnet.bulk_selected_count", { count: selectedHashes.length })}
                        </span>
                    </div>
                    <div class="flex items-center gap-2 shrink-0">
                        <button
                            type="button"
                            class="inline-flex items-center whitespace-nowrap rounded px-0 py-0.5 text-xs font-bold leading-none text-yellow-600 dark:text-yellow-400 hover:underline disabled:pointer-events-none disabled:opacity-40"
                            disabled={selectedHashes.length === 0}
                            onclick={bulkAddFavourites}
                        >
                            {t("nomadnet.bulk_add_to_favourites")}
                        </button>
                        <button
                            type="button"
                            class="inline-flex items-center whitespace-nowrap rounded px-0 py-0.5 text-xs font-bold leading-none text-red-600 dark:text-red-400 hover:underline disabled:pointer-events-none disabled:opacity-40"
                            disabled={selectedHashes.length === 0}
                            onclick={bulkBlockNodes}
                        >
                            {t("nomadnet.bulk_block_nodes")}
                        </button>
                    </div>
                </div>
            </div>
        {/if}
    </div>

    <div class="flex-1 min-h-0 px-2 pb-4 overflow-y-auto" onscroll={handleScroll}>
        {#if searchedNodes.length > 0}
            <div class="space-y-2 pt-2">
                {#each searchedNodes as node (node.destination_hash)}
                    <NomadAnnounceRow
                        {node}
                        selected={node.destination_hash === selectedDestinationHash}
                        {selectionMode}
                        isSelectedInBulk={selectedHashSet.has(node.destination_hash)}
                        isDropdownActive={activeDropdownHash === node.destination_hash}
                        isBlockedNode={isBlocked(node.identity_hash || node.destination_hash)}
                        isFav={isFavourite(node.destination_hash)}
                        onclick={() => onnodeclick?.(node)}
                        oncontextmenu={(e) => {
                            e.preventDefault();
                            openContextMenu(e, node);
                        }}
                        ontoggleselect={() => toggleSelect(node.destination_hash)}
                        ontoggledropdown={(e) => {
                            e.stopPropagation();
                            activeDropdownHash =
                                activeDropdownHash === node.destination_hash ? null : node.destination_hash;
                        }}
                        {onaddfavourite}
                    />
                {/each}
            </div>

            {#if isLoadingMoreNodes}
                <div class="py-4 flex justify-center text-gray-400">
                    <MaterialDesignIcon iconName="loading" class="size-6 animate-spin" />
                </div>
            {/if}
        {:else}
            <div class="text-center py-8 text-sm text-gray-400">
                {nodesSearchTerm ? t("nomadnet.no_announces_found") : t("nomadnet.no_announces_yet")}
            </div>
        {/if}
    </div>
</div>

{#if contextMenu.show && contextMenu.node}
    <NomadAnnounceContextMenu
        node={contextMenu.node}
        left={menuLeft}
        top={menuTop}
        caret={menuCaret}
        isFav={isFavourite(contextMenu.node.destination_hash)}
        isBlockedNode={isBlocked(contextMenu.node.identity_hash || contextMenu.node.destination_hash)}
        bind:panel={menuPanel}
        {onaddfavourite}
        onclose={closeContextMenu}
    />
{/if}
