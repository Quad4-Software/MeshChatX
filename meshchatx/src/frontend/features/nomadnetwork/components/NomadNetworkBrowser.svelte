<!-- SPDX-License-Identifier: 0BSD -->
<script lang="ts">
    import { onMount, onDestroy, untrack } from "svelte";
    import GlobalEmitter from "../../../js/GlobalEmitter.js";
    import GlobalState from "../../../js/GlobalState.js";
    import { onWsEvent, offWsEvent } from "../../../js/registries/wsEventRegistry.js";
    import { getCurrentRoute } from "../../../shell/hashRouter.js";
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
        calculateRelativeTabIndex,
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
    import LinkUtils from "../../../js/LinkUtils.js";
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
    const tabsEnabled = $derived(GlobalState.config?.nomad_tabs_enabled !== false);

    // Match the Vue browser: the tab strip only shows on wide viewports.
    let isWideViewport = $state(false);
    const showTabStrip = $derived(!isPopout && isWideViewport && tabsEnabled && tabs.length > 0);
    let viewportMediaQuery: MediaQueryList | null = null;
    let viewportMediaQueryListener: ((event: MediaQueryListEvent) => void) | null = null;

    function setupViewportWatcher() {
        if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
            isWideViewport = false;
            return;
        }
        viewportMediaQuery = window.matchMedia("(min-width: 768px)");
        isWideViewport = viewportMediaQuery.matches;
        viewportMediaQueryListener = (event) => {
            isWideViewport = event.matches;
        };
        viewportMediaQuery.addEventListener("change", viewportMediaQueryListener);
    }

    function teardownViewportWatcher() {
        if (viewportMediaQuery && viewportMediaQueryListener) {
            viewportMediaQuery.removeEventListener("change", viewportMediaQueryListener);
        }
        viewportMediaQuery = null;
        viewportMediaQueryListener = null;
    }

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

    function handleTabReorder(fromIndex: number, toIndex: number) {
        if (fromIndex === toIndex || fromIndex < 0 || toIndex < 0) return;
        if (fromIndex >= tabs.length || toIndex >= tabs.length) return;
        const next = [...tabs];
        const [moved] = next.splice(fromIndex, 1);
        next.splice(toIndex, 0, moved);
        applyTabList({ tabs: next, selectedTabId });
    }

    function selectRelativeTab(offset: number) {
        const nextIndex = calculateRelativeTabIndex(tabs, selectedTabId, offset);
        if (nextIndex >= 0) {
            applyTabList({ tabs, selectedTabId: tabs[nextIndex].id });
        }
    }

    function selectTabByIndex(index: number) {
        if (index >= 0 && index < tabs.length) {
            applyTabList({ tabs, selectedTabId: tabs[index].id });
        }
    }

    // Browser-style tab shortcuts. The keepAlive page stays mounted on other
    // routes, so gate on the current route name like the Vue port did.
    function handleKeydown(event: KeyboardEvent) {
        if (!tabsEnabled || getCurrentRoute()?.name !== "nomadnetwork") {
            return;
        }

        const isMac = navigator.platform.toUpperCase().indexOf("MAC") >= 0;
        const mod = isMac ? event.metaKey : event.ctrlKey;
        const hasModifier = event.ctrlKey || event.metaKey || event.altKey;
        const activeElement = document.activeElement as HTMLElement | null;
        const isInput =
            !!activeElement &&
            (["INPUT", "TEXTAREA"].includes(activeElement.tagName) || activeElement.isContentEditable);
        if (isInput && !hasModifier) {
            return;
        }

        const key = event.key.toLowerCase();

        if (mod && key === "t") {
            event.preventDefault();
            event.stopPropagation();
            handleNewTab("", DEFAULT_PAGE_PATH, false);
            return;
        }
        if (mod && event.shiftKey && key === "p") {
            event.preventDefault();
            event.stopPropagation();
            handleNewTab("", DEFAULT_PAGE_PATH, true);
            return;
        }
        if (mod && key === "w") {
            event.preventDefault();
            event.stopPropagation();
            if (selectedTabId != null) {
                handleCloseTab(selectedTabId);
            }
            return;
        }
        if (event.ctrlKey && key === "tab") {
            event.preventDefault();
            event.stopPropagation();
            selectRelativeTab(event.shiftKey ? -1 : 1);
            return;
        }
        if (event.ctrlKey && key === "pageup") {
            event.preventDefault();
            event.stopPropagation();
            selectRelativeTab(-1);
            return;
        }
        if (event.ctrlKey && key === "pagedown") {
            event.preventDefault();
            event.stopPropagation();
            selectRelativeTab(1);
            return;
        }
        if (mod && key >= "1" && key <= "9") {
            event.preventDefault();
            event.stopPropagation();
            selectTabByIndex(parseInt(key, 10) - 1);
        }
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
        // Typed http(s) URLs open externally like in-page links do; without
        // this check "https://x" parses as a bogus hash:path mesh destination.
        if (LinkUtils.httpUrlHrefOrNull(url?.trim())) {
            window.open(url.trim(), "_blank");
            return;
        }
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

    function onWebsocketReconnected() {
        void fetchNodes();
        void fetchFavourites();
    }

    // keepAlive pages are not remounted when the route target changes; the
    // onMount restore below only sees the first navigation. Re-apply the
    // route target whenever the hash, path or archive props change after that.
    let appliedRouteSignature = "";
    const routeHashWatchReady = $derived(
        [destinationHash || "", routePath, routeArchiveId ?? "", routeQuery.newTab || ""].join("|")
    );

    function applyRouteTarget() {
        const targetHash = destinationHash || "";
        const targetPath = routePath || DEFAULT_PAGE_PATH;
        const forceNewTab = routeQuery.newTab === "1";
        if (targetHash) {
            if (tabs.length === 0 || forceNewTab) {
                handleNewTab(targetHash, targetPath, false, routeArchiveId);
            } else {
                const existing = tabs.find((tab) => tab.destinationHash === targetHash);
                if (existing) {
                    existing.path = targetPath;
                    tabs = [...tabs];
                    selectedTabId = existing.id;
                    if (routeArchiveId != null) {
                        tabBootstrapArchiveId = { ...tabBootstrapArchiveId, [existing.id]: routeArchiveId };
                    }
                    persistNomadTabs(tabs, selectedTabId);
                } else {
                    handleNewTab(targetHash, targetPath, false, routeArchiveId);
                }
            }
        } else if (tabs.length === 0) {
            handleNewTab("", DEFAULT_PAGE_PATH, false);
        }
        if (selectedTabId != null) ensureTabMounted(selectedTabId);
    }

    onMount(() => {
        void fetchNodes();
        void fetchFavourites();
        setupViewportWatcher();
        window.addEventListener("keydown", handleKeydown, true);
        onWsEvent("announce", onAnnounceEvent);
        GlobalEmitter.on("identity-switched", onIdentitySwitched);
        GlobalEmitter.on("websocket-reconnected", onWebsocketReconnected);
        GlobalEmitter.on("nomadnet-add-favourite", handleAddFavourite);
        GlobalEmitter.on("nomadnet-remove-favourite", handleRemoveFavourite);
        GlobalEmitter.on("nomadnet-favourites-changed", fetchFavourites);

        const restored = restoreNomadTabs(
            destinationHash || "",
            routePath || DEFAULT_PAGE_PATH,
            routeQuery.newTab === "1"
        );
        tabs = restored.tabs;
        selectedTabId = restored.selectedTabId;
        applyRouteTarget();
        appliedRouteSignature = routeHashWatchReady;
    });

    $effect(() => {
        const signature = routeHashWatchReady;
        if (signature === appliedRouteSignature) {
            return;
        }
        appliedRouteSignature = signature;
        untrack(() => applyRouteTarget());
    });

    onDestroy(() => {
        window.removeEventListener("keydown", handleKeydown, true);
        teardownViewportWatcher();
        offWsEvent("announce", onAnnounceEvent);
        GlobalEmitter.off("identity-switched", onIdentitySwitched);
        GlobalEmitter.off("websocket-reconnected", onWebsocketReconnected);
        GlobalEmitter.off("nomadnet-add-favourite", handleAddFavourite);
        GlobalEmitter.off("nomadnet-remove-favourite", handleRemoveFavourite);
        GlobalEmitter.off("nomadnet-favourites-changed", fetchFavourites);
    });
</script>

<div class="flex h-full w-full min-h-0 min-w-0 flex-col overflow-hidden bg-sem-surface text-sem-fg">
    {#if showTabStrip}
        <NomadTabBar
            {tabs}
            {selectedTabId}
            onselecttab={handleSelectTab}
            onclosetab={handleCloseTab}
            onnewtab={() => handleNewTab("", DEFAULT_PAGE_PATH, false)}
            onnewprivatetab={() => handleNewTab("", DEFAULT_PAGE_PATH, true)}
            ontabcontextmenu={handleTabContextMenu}
            ontabreorder={handleTabReorder}
            ontabdrop={() => persistNomadTabs(tabs, selectedTabId)}
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
        showTabActions={showTabStrip}
        canCloseTabsRight={(() => {
            const idx = tabContextMenu.tabId !== null ? tabs.findIndex((t) => t.id === tabContextMenu.tabId) : -1;
            return idx >= 0 && idx < tabs.length - 1;
        })()}
        canCloseOtherTabs={tabs.length > 1 && tabContextMenu.tabId !== null}
        canCloseAllTabs={tabs.length > 1}
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
