<!-- SPDX-License-Identifier: 0BSD -->

<script module lang="ts">
    // Remember the last picked sidebar tab for this session so a fresh sidebar
    // (new tab, remount) reopens where the user left off instead of Favourites.
    let lastSidebarTab: "favourites" | "announces" = "favourites";
</script>

<script lang="ts">
    import { onMount } from "svelte";
    import { useEventListener } from "runed";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import IconButton from "../../../ui/svelte/IconButton.svelte";
    import GlobalEmitter from "../../../js/GlobalEmitter.js";
    import { t } from "../../../js/i18n.js";
    import NomadNetworkSidebarFavourites from "./NomadNetworkSidebarFavourites.svelte";
    import NomadNetworkSidebarAnnounces from "./NomadNetworkSidebarAnnounces.svelte";
    import { favouriteDisplayName } from "../lib/nomadSidebarFavourites.js";
    import DialogUtils from "../../../js/DialogUtils.js";
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
        collapsed?: boolean;
        class?: string;
        onnodeclick?: (node: NomadNode) => void;
        onrenamefavourite?: (fav: NomadFavourite) => void;
        onremovefavourite?: (fav: NomadFavourite) => void;
        onaddfavourite?: (node: NomadNode) => void;
        ontoggleidentifyonconnect?: (hash: string) => void;
        onnodessearchchanged?: (term: string) => void;
        onloadmorenodes?: () => void;
        onnavigateurl?: (url: string) => void;
        ontogglecollapse?: () => void;
        onbulkremovefavourites?: (hashes: string[]) => void;
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
        collapsed = false,
        class: className = "",
        onnodeclick,
        onrenamefavourite,
        onremovefavourite,
        onaddfavourite,
        ontoggleidentifyonconnect,
        onnodessearchchanged,
        onloadmorenodes,
        onnavigateurl,
        ontogglecollapse,
        onbulkremovefavourites,
        onbulkaddfavourites,
    }: Props = $props();

    let tab = $state<"favourites" | "announces">(lastSidebarTab);
    let mobileUrlInput = $state("");

    function submitMobileUrl() {
        const url = mobileUrlInput.trim();
        if (!url) {
            return;
        }
        mobileUrlInput = "";
        onnavigateurl?.(url);
    }
    let smUp = $state(typeof window !== "undefined" ? window.innerWidth >= 640 : true);

    const effectiveCollapsed = $derived(collapsed && smUp);

    const sidebarRootClass = $derived(
        [
            effectiveCollapsed
                ? "flex flex-col w-16 min-w-16 max-w-16 h-full min-h-0 bg-sem-surface border-r border-sem-border"
                : "flex flex-col w-full sm:w-80 sm:min-w-80 md:max-lg:w-64 md:max-lg:min-w-64 lg:w-80 lg:min-w-80 min-h-0 bg-sem-surface border-r border-sem-border",
            selectedDestinationHash ? "max-sm:hidden" : "",
        ]
            .filter(Boolean)
            .join(" ")
    );

    const collapsedFavouritesPreview = $derived(favourites.slice(0, 5));
    const collapsedAnnounceNodesPreview = $derived.by(() => {
        const list = Object.values(nodes);
        list.sort((a, b) => {
            const ta = a.updated_at ? new Date(a.updated_at).getTime() : 0;
            const tb = b.updated_at ? new Date(b.updated_at).getTime() : 0;
            return tb - ta;
        });
        return list.slice(0, 5);
    });

    let mql = $state<MediaQueryList | null>(null);
    function onResize() {
        if (mql) smUp = mql.matches || (typeof window !== "undefined" && window.innerWidth >= 640);
    }

    useEventListener(() => mql, "change", onResize);

    $effect(() => {
        lastSidebarTab = tab;
    });

    onMount(() => {
        if (typeof window !== "undefined") {
            if (typeof window.matchMedia === "function") {
                mql = window.matchMedia("(min-width: 640px)");
                if (mql) {
                    smUp = mql.matches || window.innerWidth >= 640;
                }
            } else {
                smUp = window.innerWidth >= 640;
            }
        }
    });
</script>

<div class="{sidebarRootClass} {className}">
    {#if effectiveCollapsed}
        <div class="flex flex-col h-full min-h-0 bg-sem-surface border-r border-sem-border">
            <div class="hidden sm:flex h-10 shrink-0 items-center justify-center border-b border-sem-border px-2">
                <button
                    type="button"
                    class="p-1.5 rounded-lg text-gray-500 hover:bg-gray-100 text-sem-fg-muted dark:hover:bg-zinc-800 transition-colors"
                    onclick={() => ontogglecollapse?.()}
                >
                    <MaterialDesignIcon iconName="chevron-right" class="size-5" />
                </button>
            </div>
            <div class="flex flex-col items-center gap-1 py-2 px-1 border-b border-sem-border">
                <button
                    type="button"
                    class="p-2 rounded-xl transition-colors {tab === 'favourites'
                        ? 'bg-blue-600 text-white dark:bg-blue-500'
                        : 'text-gray-500 hover:bg-gray-100 text-sem-fg-muted dark:hover:bg-zinc-800'}"
                    onclick={() => {
                        tab = "favourites";
                    }}
                >
                    <MaterialDesignIcon iconName="star" class="size-6" />
                </button>
                <button
                    type="button"
                    class="p-2 rounded-xl transition-colors {tab === 'announces'
                        ? 'bg-blue-600 text-white dark:bg-blue-500'
                        : 'text-gray-500 hover:bg-gray-100 text-sem-fg-muted dark:hover:bg-zinc-800'}"
                    onclick={() => {
                        tab = "announces";
                    }}
                >
                    <MaterialDesignIcon iconName="satellite-uplink" class="size-6" />
                </button>
            </div>
            {#if tab === "favourites"}
                <div
                    class="flex-1 min-h-0 w-full overflow-y-auto overflow-x-hidden flex flex-col items-center gap-1 py-1 px-0.5"
                >
                    {#each collapsedFavouritesPreview as fav (fav.destination_hash)}
                        <button
                            type="button"
                            class="shrink-0 p-1 rounded-xl transition-colors focus:outline-hidden focus-visible:ring-2 focus-visible:ring-blue-500 {fav.destination_hash ===
                            selectedDestinationHash
                                ? 'ring-2 ring-blue-500 ring-offset-1 ring-offset-white dark:ring-offset-zinc-950'
                                : 'hover:bg-white/10'}"
                            title={favouriteDisplayName(fav, nodes[fav.destination_hash], t("nomadnet.unknown_node"))}
                            onclick={() => onnodeclick?.(fav)}
                        >
                            <MaterialDesignIcon iconName="server-network" class="size-6 text-sem-fg-muted" />
                        </button>
                    {/each}
                </div>
            {:else if tab === "announces"}
                <div
                    class="flex-1 min-h-0 w-full overflow-y-auto overflow-x-hidden flex flex-col items-center gap-1 py-1 px-0.5"
                >
                    {#each collapsedAnnounceNodesPreview as node (node.destination_hash)}
                        <button
                            type="button"
                            class="shrink-0 p-1 rounded-xl transition-colors focus:outline-hidden focus-visible:ring-2 focus-visible:ring-blue-500 {node.destination_hash ===
                            selectedDestinationHash
                                ? 'ring-2 ring-blue-500 ring-offset-1 ring-offset-white dark:ring-offset-zinc-950'
                                : 'hover:bg-white/10'}"
                            title={node.custom_display_name || node.display_name}
                            onclick={() => onnodeclick?.(node)}
                        >
                            <MaterialDesignIcon iconName="satellite-uplink" class="size-6 text-sem-fg-muted" />
                        </button>
                    {/each}
                </div>
            {/if}
        </div>
    {:else}
        <div class="-mb-px flex h-10 min-w-0 items-stretch border-b border-sem-border bg-sem-surface">
            <div class="flex min-w-0 flex-1">
                <button
                    type="button"
                    class="sidebar-tab flex h-full w-1/2 items-center justify-center text-sm font-medium border-b-2 transition {tab ===
                    'favourites'
                        ? 'text-blue-600 border-blue-500 dark:text-blue-300 dark:border-blue-400'
                        : 'text-sem-fg-muted border-transparent'}"
                    onclick={() => {
                        tab = "favourites";
                    }}
                >
                    {t("nomadnet.favourites")}
                </button>
                <button
                    type="button"
                    class="sidebar-tab flex h-full w-1/2 items-center justify-center text-sm font-medium border-b-2 transition {tab ===
                    'announces'
                        ? 'text-blue-600 border-blue-500 dark:text-blue-300 dark:border-blue-400'
                        : 'text-sem-fg-muted border-transparent'}"
                    onclick={() => {
                        tab = "announces";
                    }}
                >
                    {t("nomadnet.announces")}
                </button>
            </div>
            <button
                type="button"
                class="hidden sm:flex shrink-0 items-center border-b-2 border-transparent px-1.5 text-gray-500 hover:bg-gray-100 text-sem-fg-muted dark:hover:bg-zinc-800 transition-colors"
                onclick={() => ontogglecollapse?.()}
            >
                <MaterialDesignIcon iconName="chevron-left" class="size-5" />
            </button>
        </div>

        <!-- mobile-only URL entry: below sm the viewer pane (with its
             empty-state URL input) is hidden until a node opens -->
        <div class="flex items-center gap-1.5 border-b border-sem-border px-2 py-1.5 sm:hidden">
            <input
                bind:value={mobileUrlInput}
                type="text"
                placeholder={t("nomadnet.enter_nomadnet_url")}
                class="input-field w-full min-w-0"
                onkeydown={(e) => {
                    if (e.key === "Enter") submitMobileUrl();
                }}
            />
            <IconButton title={t("nomadnet.nav_go")} class="shrink-0" onclick={submitMobileUrl}>
                <MaterialDesignIcon iconName="arrow-right" class="size-5" />
            </IconButton>
        </div>

        {#if tab === "favourites"}
            <NomadNetworkSidebarFavourites
                {favourites}
                {nodes}
                {selectedDestinationHash}
                onfavouriteclick={(fav) => onnodeclick?.(fav)}
                {onrenamefavourite}
                {onremovefavourite}
                {ontoggleidentifyonconnect}
                {onbulkremovefavourites}
                onbanishfavourite={async (fav) => {
                    if (await DialogUtils.confirm(t("nomadnet.block_node_confirm", { name: fav.display_name }))) {
                        if ((window as any).api) {
                            await (window as any).api.post("/api/v1/blocked-destinations", {
                                destination_hash: fav.destination_hash,
                            });
                        }
                        GlobalEmitter.emit("block-status-changed");
                        DialogUtils.alert(t("nomadnet.node_blocked_successfully"));
                    }
                }}
                onunblockfavourite={async (hash) => {
                    if ((window as any).api) {
                        await (window as any).api.delete(`/api/v1/blocked-destinations/${hash}`);
                    }
                    GlobalEmitter.emit("block-status-changed");
                    DialogUtils.alert(t("nomadnet.banishment_lifted"));
                }}
            />
        {:else}
            <NomadNetworkSidebarAnnounces
                {nodes}
                {favourites}
                {selectedDestinationHash}
                {nodesSearchTerm}
                {totalNodesCount}
                {isLoadingMoreNodes}
                {isSearchingNodes}
                {hasMoreNodes}
                {onnodeclick}
                {onaddfavourite}
                {onnodessearchchanged}
                {onloadmorenodes}
                {onbulkaddfavourites}
            />
        {/if}
    {/if}
</div>
