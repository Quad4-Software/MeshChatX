<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import GlobalEmitter from "../../../js/GlobalEmitter.js";
    import DialogUtils from "../../../js/DialogUtils.js";
    import { t } from "../../../js/i18n.js";
    import NomadTabBar from "./NomadTabBar.svelte";
    import NomadNetworkSidebar from "./NomadNetworkSidebar.svelte";
    import NomadNetworkPage from "./NomadNetworkPage.svelte";
    import NomadBrowserContextMenu from "./NomadBrowserContextMenu.svelte";
    import {
        restoreNomadTabs,
        persistNomadTabs,
        createNomadTab,
        closeNomadTab,
        closeTabsToRight,
        closeOtherTabs,
    } from "../lib/nomadBrowserTabs.js";
    import { DEFAULT_PAGE_PATH } from "../lib/constants.js";
    import type { NomadContextMenuState, NomadFavourite, NomadNode, NomadTab } from "../lib/types.js";

    interface Props {
        destinationHash?: string;
        path?: string;
        isPopout?: boolean;
    }

    let { destinationHash = "", path = "", isPopout = false }: Props = $props();

    let tabs = $state<NomadTab[]>([]);
    let selectedTabId = $state<number | null>(null);
    let sidebarCollapsed = $state(false);
    let nodes = $state<Record<string, NomadNode>>({});
    let favourites = $state<NomadFavourite[]>([]);
    let totalNodesCount = $state(0);
    let isLoadingMoreNodes = $state(false);
    let isSearchingNodes = $state(false);
    let hasMoreNodes = $state(false);
    let nodesSearchTerm = $state("");

    let tabContextMenu = $state<NomadContextMenuState>({
        show: false,
        justOpened: false,
        x: 0,
        y: 0,
        tabId: null,
    });

    const activeTab = $derived.by(() => {
        return tabs.find((t) => t.id === selectedTabId) || null;
    });

    const contextTab = $derived.by(() => {
        if (tabContextMenu.tabId === null) return null;
        return tabs.find((t) => t.id === tabContextMenu.tabId) || null;
    });

    async function fetchNodes() {
        const api = (window as any).api;
        if (!api) return;
        try {
            const res = await api.get("/api/v1/page-nodes");
            const list: NomadNode[] = res.data?.nodes || res.data || [];
            const map: Record<string, NomadNode> = {};
            for (const n of list) {
                if (n.destination_hash) map[n.destination_hash] = n;
            }
            nodes = map;
            totalNodesCount = Object.keys(map).length;
        } catch {
            // keep existing
        }
    }

    async function fetchFavourites() {
        const api = (window as any).api;
        if (!api) return;
        try {
            const res = await api.get("/api/v1/favourites");
            favourites = res.data?.favourites || res.data || [];
        } catch {
            favourites = [];
        }
    }

    function handleSelectTab(id: number) {
        selectedTabId = id;
        persistNomadTabs(tabs, selectedTabId);
    }

    function handleNewTab(dHash: string = "", pPath: string = DEFAULT_PAGE_PATH, isPrivate: boolean = false) {
        const newTab = createNomadTab(dHash, pPath, isPrivate);
        tabs = [...tabs, newTab];
        selectedTabId = newTab.id;
        persistNomadTabs(tabs, selectedTabId);
    }

    function handleCloseTab(id: number) {
        const next = closeNomadTab(tabs, selectedTabId, id);
        tabs = next.tabs;
        selectedTabId = next.selectedTabId;
        persistNomadTabs(tabs, selectedTabId);
    }

    function handleNodeClick(node: NomadNode | NomadFavourite) {
        if (!node.destination_hash) return;
        if (activeTab) {
            activeTab.destinationHash = node.destination_hash;
            activeTab.path = DEFAULT_PAGE_PATH;
            activeTab.title = node.custom_display_name || node.display_name || node.destination_hash;
            tabs = [...tabs];
            persistNomadTabs(tabs, selectedTabId);
        } else {
            handleNewTab(node.destination_hash, DEFAULT_PAGE_PATH, false);
        }
    }

    async function handleAddFavourite(node: NomadNode) {
        const api = (window as any).api;
        if (!api || !node.destination_hash) return;
        try {
            await api.post("/api/v1/favourites", {
                destination_hash: node.destination_hash,
                display_name: node.custom_display_name || node.display_name,
            });
            fetchFavourites();
        } catch {
            // failed
        }
    }

    async function handleRemoveFavourite(fav: NomadFavourite) {
        const api = (window as any).api;
        if (!api || !fav.destination_hash) return;
        if (await DialogUtils.confirm(t("nomadnet.remove_favourite_confirm", { name: fav.display_name }))) {
            try {
                await api.delete(`/api/v1/favourites/${fav.destination_hash}`);
                fetchFavourites();
            } catch {
                // failed
            }
        }
    }

    async function handleRenameFavourite(fav: NomadFavourite) {
        const api = (window as any).api;
        if (!api || !fav.destination_hash) return;
        const newName = await DialogUtils.prompt(
            t("nomadnet.rename_favourite_prompt"),
            fav.custom_display_name || fav.display_name || ""
        );
        if (newName !== null) {
            try {
                await api.put(`/api/v1/favourites/${fav.destination_hash}`, {
                    custom_display_name: newName.trim() || null,
                });
                fetchFavourites();
            } catch {
                // failed
            }
        }
    }

    function handleTabContextMenu(e: MouseEvent, tabId: number) {
        e.preventDefault();
        tabContextMenu = {
            show: true,
            justOpened: true,
            x: e.clientX,
            y: e.clientY,
            tabId,
        };
        setTimeout(() => {
            tabContextMenu.justOpened = false;
        }, 50);
    }

    function handleWsMessage(event: CustomEvent) {
        const data = event.detail;
        if (!data) return;
        if (data.type === "nomadnet.page_node_announced") {
            if (data.node?.destination_hash) {
                nodes[data.node.destination_hash] = {
                    ...nodes[data.node.destination_hash],
                    ...data.node,
                };
                nodes = { ...nodes };
            }
        }
    }

    function onIdentitySwitched() {
        tabs = [];
        selectedTabId = null;
        nodes = {};
        favourites = [];
        handleNewTab("", DEFAULT_PAGE_PATH, false);
        void fetchNodes();
        void fetchFavourites();
    }

    onMount(() => {
        void fetchNodes();
        void fetchFavourites();
        GlobalEmitter.on("ws-message", handleWsMessage);
        GlobalEmitter.on("identity-switched", onIdentitySwitched);
        GlobalEmitter.on("nomadnet-add-favourite", handleAddFavourite);
        GlobalEmitter.on("nomadnet-remove-favourite", handleRemoveFavourite);

        const restored = restoreNomadTabs();
        tabs = restored.tabs;
        selectedTabId = restored.selectedTabId;

        if (destinationHash) {
            handleNewTab(destinationHash, path || DEFAULT_PAGE_PATH, false);
        } else if (tabs.length === 0) {
            handleNewTab("", DEFAULT_PAGE_PATH, false);
        }
    });

    onDestroy(() => {
        GlobalEmitter.off("ws-message", handleWsMessage);
        GlobalEmitter.off("identity-switched", onIdentitySwitched);
        GlobalEmitter.off("nomadnet-add-favourite", handleAddFavourite);
        GlobalEmitter.off("nomadnet-remove-favourite", handleRemoveFavourite);
    });
</script>

<div class="flex h-full w-full min-h-0 min-w-0 flex-col overflow-hidden bg-sem-surface text-sem-fg">
    {#if !isPopout}
        <NomadTabBar
            {tabs}
            {selectedTabId}
            onselecttab={handleSelectTab}
            onclosetab={handleCloseTab}
            onnewtab={() => handleNewTab("", DEFAULT_PAGE_PATH, false)}
            onnewprivatetab={() => handleNewTab("", DEFAULT_PAGE_PATH, true)}
            ontabcontextmenu={handleTabContextMenu}
        />
    {/if}

    <div class="flex flex-1 min-h-0 min-w-0 overflow-hidden">
        {#if !isPopout}
            <NomadNetworkSidebar
                {nodes}
                {favourites}
                selectedDestinationHash={activeTab?.destinationHash}
                {nodesSearchTerm}
                {totalNodesCount}
                {isLoadingMoreNodes}
                {isSearchingNodes}
                {hasMoreNodes}
                collapsed={sidebarCollapsed}
                onnodeclick={handleNodeClick}
                onaddfavourite={handleAddFavourite}
                onremovefavourite={handleRemoveFavourite}
                onrenamefavourite={handleRenameFavourite}
                ontogglecollapse={() => {
                    sidebarCollapsed = !sidebarCollapsed;
                }}
                onnodessearchchanged={(v) => {
                    nodesSearchTerm = v;
                }}
            />
        {/if}

        <div class="flex-1 min-h-0 min-w-0 flex flex-col overflow-hidden">
            {#if activeTab}
                <NomadNetworkPage
                    destinationHash={activeTab.destinationHash}
                    pagePath={activeTab.path || DEFAULT_PAGE_PATH}
                    active={true}
                    {isPopout}
                    isPrivate={activeTab.private}
                    tabState={activeTab}
                    {favourites}
                    {nodes}
                    onnavigate={(dHash, pPath, isPriv) => {
                        if (activeTab) {
                            activeTab.destinationHash = dHash;
                            activeTab.path = pPath || DEFAULT_PAGE_PATH;
                            if (isPriv !== undefined) activeTab.private = isPriv;
                            tabs = [...tabs];
                            persistNomadTabs(tabs, selectedTabId);
                        }
                    }}
                    ontabtitlechange={(title) => {
                        if (activeTab) {
                            activeTab.title = title;
                            tabs = [...tabs];
                            persistNomadTabs(tabs, selectedTabId);
                        }
                    }}
                    onclose={() => {
                        if (activeTab) handleCloseTab(activeTab.id);
                    }}
                />
            {:else}
                <div class="flex-1 flex items-center justify-center text-sem-fg-muted p-8 text-center">
                    <div>
                        <div class="text-xl font-semibold mb-2">{t("nomadnet.welcome_to_nomadnet")}</div>
                        <div class="text-sm max-w-md">{t("nomadnet.select_node_or_enter_url")}</div>
                    </div>
                </div>
            {/if}
        </div>
    </div>

    <NomadBrowserContextMenu
        show={tabContextMenu.show}
        x={tabContextMenu.x}
        y={tabContextMenu.y}
        justOpened={tabContextMenu.justOpened}
        hasActivePage={false}
        canFavourite={false}
        isFavourite={false}
        canDownloadPage={false}
        showTabActions={true}
        canCloseTabsRight={tabContextMenu.tabId !== null &&
            tabs.findIndex((t) => t.id === tabContextMenu.tabId) < tabs.length - 1}
        canCloseOtherTabs={tabs.length > 1}
        canCloseAllTabs={tabs.length > 0}
        contextTabIsPrivate={contextTab?.private}
        onclose={() => {
            tabContextMenu.show = false;
        }}
        onnewprivatetab={() => {
            tabContextMenu.show = false;
            handleNewTab("", DEFAULT_PAGE_PATH, true);
        }}
        onclosetabsright={() => {
            if (tabContextMenu.tabId !== null) {
                const next = closeTabsToRight(tabs, selectedTabId, tabContextMenu.tabId);
                tabs = next.tabs;
                selectedTabId = next.selectedTabId;
                persistNomadTabs(tabs, selectedTabId);
            }
            tabContextMenu.show = false;
        }}
        oncloseothertabs={() => {
            if (tabContextMenu.tabId !== null) {
                const next = closeOtherTabs(tabs, tabContextMenu.tabId);
                tabs = next.tabs;
                selectedTabId = next.selectedTabId;
                persistNomadTabs(tabs, selectedTabId);
            }
            tabContextMenu.show = false;
        }}
        onclosealltabs={() => {
            tabs = [];
            handleNewTab("", DEFAULT_PAGE_PATH, false);
            tabContextMenu.show = false;
        }}
    />
</div>
