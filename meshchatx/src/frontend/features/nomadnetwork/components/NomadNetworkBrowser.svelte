<!-- SPDX-License-Identifier: 0BSD -->
<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import GlobalEmitter from "../../../js/GlobalEmitter.js";
    import { onWsEvent, offWsEvent } from "../../../js/registries/wsEventRegistry.js";
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
    import {
        addNomadFavourite,
        fetchNomadFavourites,
        fetchNomadNodes,
        mergeNomadAnnounceIntoNodes,
        removeNomadFavourite,
        renameNomadFavourite,
        toggleNomadIdentifyOnConnect,
    } from "../lib/nomadBrowserData.js";
    import { DEFAULT_PAGE_PATH } from "../lib/constants.js";
    import { parseNomadUrl } from "../lib/nomadPageNavigation.js";
    import type {
        NomadContextMenuState,
        NomadFavourite,
        NomadNode,
        NomadPageContextMenuRequest,
        NomadTab,
    } from "../lib/types.js";
    interface Props {
        destinationHash?: string;
        path?: string;
        isPopout?: boolean;
        routeQuery?: Record<string, string>;
    }

    let { destinationHash = "", path = "", isPopout = false, routeQuery = {} }: Props = $props();

    let tabs = $state<NomadTab[]>([]);
    let selectedTabId = $state<number | null>(null);
    let mountedTabIds = $state<Record<number, boolean>>({});
    let sidebarCollapsed = $state(false);
    let nodes = $state<Record<string, NomadNode>>({});
    let favourites = $state<NomadFavourite[]>([]);
    let totalNodesCount = $state(0);
    let isLoadingMoreNodes = $state(false);
    let isSearchingNodes = $state(false);
    let hasMoreNodes = $state(false);
    let nodesSearchTerm = $state("");
    let tabBootstrapArchiveId = $state<Record<number, string | number | null>>({});

    let tabContextMenu = $state<NomadContextMenuState>({
        show: false,
        justOpened: false,
        x: 0,
        y: 0,
        tabId: null,
    });
    let pageContextMenu = $state<NomadPageContextMenuRequest | null>(null);

    const activeTab = $derived.by(() => {
        return tabs.find((t) => t.id === selectedTabId) || null;
    });

    const contextTab = $derived(tabs.find((t) => t.id === tabContextMenu.tabId) || null);

    const routePath = $derived(path || routeQuery.path || DEFAULT_PAGE_PATH);
    const routeArchiveId = $derived(routeQuery.archive_id || null);

    function ensureTabMounted(tabId: number | null) {
        if (tabId == null || mountedTabIds[tabId]) return;
        mountedTabIds = { ...mountedTabIds, [tabId]: true };
    }

    async function fetchNodes(append = false) {
        if (append) isLoadingMoreNodes = true;
        else if (nodesSearchTerm) isSearchingNodes = true;
        try {
            const result = await fetchNomadNodes({ append, existingNodes: nodes, searchTerm: nodesSearchTerm });
            if (!result) return;
            nodes = result.nodes;
            totalNodesCount = result.totalNodesCount;
            hasMoreNodes = result.hasMoreNodes;
        } finally {
            isLoadingMoreNodes = false;
            isSearchingNodes = false;
        }
    }

    async function fetchFavourites() {
        favourites = await fetchNomadFavourites();
    }

    function applyTabList(next: { tabs: NomadTab[]; selectedTabId: number | null }) {
        tabs = next.tabs;
        selectedTabId = next.selectedTabId;
        if (selectedTabId != null) ensureTabMounted(selectedTabId);
        persistNomadTabs(tabs, selectedTabId);
    }

    function handleSelectTab(id: number) {
        applyTabList({ tabs, selectedTabId: id });
    }

    function handleNewTab(
        dHash: string = "",
        pPath: string = DEFAULT_PAGE_PATH,
        isPrivate: boolean = false,
        archiveId: string | number | null = null
    ) {
        const newTab = createNomadTab(dHash, pPath, isPrivate);
        tabs = [...tabs, newTab];
        selectedTabId = newTab.id;
        ensureTabMounted(newTab.id);
        if (archiveId != null) {
            tabBootstrapArchiveId = { ...tabBootstrapArchiveId, [newTab.id]: archiveId };
        }
        persistNomadTabs(tabs, selectedTabId);
    }

    function handleCloseTab(id: number) {
        applyTabList(closeNomadTab(tabs, selectedTabId, id));
        const nextBootstrap = { ...tabBootstrapArchiveId };
        delete nextBootstrap[id];
        tabBootstrapArchiveId = nextBootstrap;
        const nextMounted = { ...mountedTabIds };
        delete nextMounted[id];
        mountedTabIds = nextMounted;
    }

    function activateTabForHash(hash: string, path: string, title: string | null = null) {
        if (!activeTab) return handleNewTab(hash, path || DEFAULT_PAGE_PATH, false);
        activeTab.destinationHash = hash;
        activeTab.path = path || DEFAULT_PAGE_PATH;
        activeTab.title = title;
        tabs = [...tabs];
        ensureTabMounted(activeTab.id);
        persistNomadTabs(tabs, selectedTabId);
    }

    function handleNavigateUrl(url: string) {
        const { destinationHash: dHash, pagePath: pPath } = parseNomadUrl(url);
        const targetHash = dHash || activeTab?.destinationHash || "";
        if (!targetHash) return;
        activateTabForHash(targetHash, pPath || DEFAULT_PAGE_PATH, activeTab?.title ?? null);
    }

    function handleNodeClick(node: NomadNode | NomadFavourite) {
        if (!node.destination_hash) return;
        const title = node.custom_display_name || node.display_name || node.destination_hash;
        activateTabForHash(node.destination_hash, DEFAULT_PAGE_PATH, title || null);
    }

    async function handleAddFavourite(node: NomadNode) {
        if (await addNomadFavourite(node)) await fetchFavourites();
    }

    async function handleRemoveFavourite(fav: NomadFavourite) {
        if (await removeNomadFavourite(fav)) await fetchFavourites();
    }

    async function handleRenameFavourite(fav: NomadFavourite) {
        if (await renameNomadFavourite(fav)) await fetchFavourites();
    }

    async function handleToggleIdentifyOnConnect(hash: string) {
        if (await toggleNomadIdentifyOnConnect(hash, favourites)) await fetchFavourites();
    }

    function openBrowserContextMenu(
        x: number,
        y: number,
        tabId: number | null,
        page: NomadPageContextMenuRequest | null = null
    ) {
        tabContextMenu = { show: true, justOpened: true, x, y, tabId };
        pageContextMenu = page;
        setTimeout(() => {
            tabContextMenu.justOpened = false;
        }, 50);
    }

    function handleTabContextMenu(e: MouseEvent, tabId: number) {
        e.preventDefault();
        openBrowserContextMenu(e.clientX, e.clientY, tabId);
    }

    function onAnnounceEvent(json: Record<string, unknown>) {
        const next = mergeNomadAnnounceIntoNodes(nodes, json);
        if (next) nodes = next;
    }

    function resetNomadTabs() {
        tabs = [];
        selectedTabId = null;
        mountedTabIds = {};
        tabBootstrapArchiveId = {};
    }

    function onIdentitySwitched() {
        resetNomadTabs();
        nodes = {};
        favourites = [];
        handleNewTab("", DEFAULT_PAGE_PATH, false);
        void fetchNodes();
        void fetchFavourites();
    }

    onMount(() => {
        void fetchNodes();
        void fetchFavourites();
        onWsEvent("announce", onAnnounceEvent);
        GlobalEmitter.on("identity-switched", onIdentitySwitched);
        GlobalEmitter.on("nomadnet-add-favourite", handleAddFavourite);
        GlobalEmitter.on("nomadnet-remove-favourite", handleRemoveFavourite);
        GlobalEmitter.on("nomadnet-favourites-changed", fetchFavourites);

        const initialHash = destinationHash || "";
        const initialPath = routePath || DEFAULT_PAGE_PATH;
        const forceNewTab = routeQuery.newTab === "1";
        const restored = restoreNomadTabs(initialHash, initialPath, forceNewTab);
        tabs = restored.tabs;
        selectedTabId = restored.selectedTabId;

        if (initialHash) {
            if (tabs.length === 0 || forceNewTab) {
                handleNewTab(initialHash, initialPath, false, routeArchiveId);
            } else {
                const existing = tabs.find((tab) => tab.destinationHash === initialHash);
                if (existing) {
                    existing.path = initialPath;
                    tabs = [...tabs];
                    selectedTabId = existing.id;
                    if (routeArchiveId != null) {
                        tabBootstrapArchiveId = { ...tabBootstrapArchiveId, [existing.id]: routeArchiveId };
                    }
                    persistNomadTabs(tabs, selectedTabId);
                } else {
                    handleNewTab(initialHash, initialPath, false, routeArchiveId);
                }
            }
        } else if (tabs.length === 0) {
            handleNewTab("", DEFAULT_PAGE_PATH, false);
        }
        if (selectedTabId != null) ensureTabMounted(selectedTabId);
    });

    onDestroy(() => {
        offWsEvent("announce", onAnnounceEvent);
        GlobalEmitter.off("identity-switched", onIdentitySwitched);
        GlobalEmitter.off("nomadnet-add-favourite", handleAddFavourite);
        GlobalEmitter.off("nomadnet-remove-favourite", handleRemoveFavourite);
        GlobalEmitter.off("nomadnet-favourites-changed", fetchFavourites);
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
                ontoggleidentifyonconnect={(hash) => void handleToggleIdentifyOnConnect(hash)}
                ontogglecollapse={() => {
                    sidebarCollapsed = !sidebarCollapsed;
                }}
                onnodessearchchanged={(v) => {
                    nodesSearchTerm = v;
                    void fetchNodes(false);
                }}
                onloadmorenodes={() => void fetchNodes(true)}
                onnavigateurl={handleNavigateUrl}
            />
        {/if}

        <div class="relative flex-1 min-h-0 min-w-0 overflow-hidden">
            {#each tabs as tab (tab.id)}
                {#if mountedTabIds[tab.id]}
                    <div
                        class="absolute inset-0 flex min-h-0 min-w-0 flex-col {!tab.destinationHash
                            ? 'max-sm:pointer-events-none max-sm:invisible'
                            : ''}"
                        class:hidden={tab.id !== selectedTabId}
                    >
                        <NomadNetworkPage
                            destinationHash={tab.destinationHash}
                            pagePath={tab.path || DEFAULT_PAGE_PATH}
                            active={tab.id === selectedTabId}
                            {isPopout}
                            isPrivate={tab.private}
                            tabState={tab}
                            {favourites}
                            {nodes}
                            bootstrapArchiveId={tabBootstrapArchiveId[tab.id] ?? null}
                            onnavigate={(dHash, pPath, isPriv) => {
                                tab.destinationHash = dHash;
                                tab.path = pPath || DEFAULT_PAGE_PATH;
                                if (isPriv !== undefined) tab.private = isPriv;
                                tabs = [...tabs];
                                persistNomadTabs(tabs, selectedTabId);
                            }}
                            ontabtitlechange={(title) => {
                                tab.title = title;
                                tabs = [...tabs];
                                persistNomadTabs(tabs, selectedTabId);
                            }}
                            onclose={() => handleCloseTab(tab.id)}
                            onfavouriteschanged={() => void fetchFavourites()}
                            onpagecontextmenu={(menu) =>
                                openBrowserContextMenu(menu.clientX, menu.clientY, tab.id, menu)}
                        />
                    </div>
                {/if}
            {/each}
            {#if !activeTab}
                <div
                    class="flex-1 flex items-center justify-center text-sem-fg-muted p-8 text-center text-xl font-semibold"
                >
                    {t("nomadnet.welcome_to_nomadnet")}
                </div>
            {/if}
        </div>
    </div>

    <NomadBrowserContextMenu
        show={tabContextMenu.show}
        x={tabContextMenu.x}
        y={tabContextMenu.y}
        justOpened={tabContextMenu.justOpened}
        hasActivePage={pageContextMenu?.hasActivePage ?? false}
        canFavourite={pageContextMenu?.canFavourite ?? false}
        isFavourite={pageContextMenu?.isFavourite ?? false}
        canDownloadPage={pageContextMenu?.canDownloadPage ?? false}
        showTabActions={true}
        canCloseTabsRight={tabContextMenu.tabId !== null &&
            tabs.findIndex((t) => t.id === tabContextMenu.tabId) < tabs.length - 1}
        canCloseOtherTabs={tabs.length > 1}
        canCloseAllTabs={tabs.length > 0}
        contextTabIsPrivate={contextTab?.private}
        onclose={() => {
            tabContextMenu.show = false;
        }}
        onviewsource={() => pageContextMenu?.viewSource()}
        onreload={() => pageContextMenu?.reload()}
        onfavorite={() => pageContextMenu?.favorite()}
        ondownloadpage={() => pageContextMenu?.downloadPage()}
        onnewprivatetab={() => {
            tabContextMenu.show = false;
            handleNewTab("", DEFAULT_PAGE_PATH, true);
        }}
        onclosetabsright={() => {
            if (tabContextMenu.tabId !== null) {
                applyTabList(closeTabsToRight(tabs, selectedTabId, tabContextMenu.tabId));
            }
            tabContextMenu.show = false;
        }}
        oncloseothertabs={() => {
            if (tabContextMenu.tabId !== null) {
                applyTabList(closeOtherTabs(tabs, tabContextMenu.tabId));
            }
            tabContextMenu.show = false;
        }}
        onclosealltabs={() => {
            resetNomadTabs();
            handleNewTab("", DEFAULT_PAGE_PATH, false);
            tabContextMenu.show = false;
        }}
    />
</div>
