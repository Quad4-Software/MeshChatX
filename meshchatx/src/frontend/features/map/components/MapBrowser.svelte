<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy, tick } from "svelte";
    import MapPage from "../MapPage.svelte";
    import MapTabBar from "./MapTabBar.svelte";
    import TileCache from "../../../js/TileCache.js";
    import GlobalEmitter from "../../../js/GlobalEmitter.js";
    import GlobalState from "../../../js/GlobalState.js";
    import { loadMapTabs, saveMapTabs } from "../../../js/browserLayoutStore.js";
    import { LEGACY_MAP_STATE_KEY, legacyMapTabStateKey, mapViewStateKey } from "../../../js/mapStateKeys.js";
    import { t } from "../../../js/i18n.js";
    import { DOUBLE_TAP_MS, MAX_MAP_TABS } from "../lib/constants.js";
    import type { MapTab } from "../lib/types.js";

    interface Props {
        route?: any;
    }

    let { route: _route = null }: Props = $props();

    let tabs = $state<MapTab[]>([]);
    let activeTabId = $state<number | null>(null);
    let nextTabId = 1;
    let nextTabNumber = 1;
    let isWideViewport = $state(false);
    let mediaQuery: MediaQueryList | null = null;
    let mediaQueryListener: ((event: MediaQueryListEvent) => void) | null = null;
    let renamingTabId = $state<number | null>(null);
    let renameDraft = $state("");
    let lastLabelTap = { tabId: null as number | null, time: 0 };
    let isRouteActive = $state(true);
    let renameInputEl = $state<HTMLInputElement | null>(null);

    const showTabStrip = $derived(isWideViewport && tabs.length > 0);
    const canAddTab = $derived(tabs.length < MAX_MAP_TABS);
    const _activeTab = $derived(tabs.find((tab) => tab.id === activeTabId) || null);

    const tabLayoutSignature = $derived.by(() => {
        const tabsStr = tabs
            .map((tab) => `${tab.storageId || ""}|${tab.title || ""}|${tab.userRenamed ? "1" : "0"}`)
            .join("\u241f");
        const activeIndex = tabs.findIndex((tab) => tab.id === activeTabId);
        return `${activeIndex}\u241e${tabsStr}`;
    });

    $effect(() => {
        if (tabLayoutSignature) {
            persistTabs();
        }
    });

    function createStorageId(): string {
        if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
            return crypto.randomUUID();
        }
        return `map-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    }

    function defaultTabTitle(tabNumber = nextTabNumber): string {
        return t("map.tab_default_name", { number: tabNumber });
    }

    export function addTab(
        title: string | null = null,
        activate = true,
        storageId: string | null = null
    ): number | null {
        if (tabs.length >= MAX_MAP_TABS) {
            return null;
        }
        const tabNumber = nextTabNumber++;
        const id = nextTabId++;
        const resolvedStorageId = storageId || createStorageId();
        const newTab: MapTab = {
            id,
            storageId: resolvedStorageId,
            title: title || defaultTabTitle(tabNumber),
            userRenamed: Boolean(title),
            tabNumber,
        };
        tabs.push(newTab);
        if (activate) {
            activeTabId = id;
        }
        return id;
    }

    export function tabTitle(tab: { title?: string | null }): string {
        if (tab.title) {
            return tab.title;
        }
        return t("map.new_tab");
    }

    export function onMapUpdateTitle(tabId: number, title: string) {
        const tab = tabs.find((entry) => entry.id === tabId);
        if (!tab || tab.userRenamed) {
            return;
        }
        const trimmed = typeof title === "string" ? title.trim() : "";
        if (!trimmed) {
            return;
        }
        tab.title = trimmed.slice(0, 64);
    }

    export async function startRename(tabId: number) {
        const tab = tabs.find((entry) => entry.id === tabId);
        if (!tab) return;
        renamingTabId = tabId;
        renameDraft = tabTitle(tab);
        await tick();
        renameInputEl?.focus();
        renameInputEl?.select();
    }

    export function commitRename() {
        if (renamingTabId == null) return;
        const tab = tabs.find((entry) => entry.id === renamingTabId);
        if (tab) {
            const trimmed = renameDraft.trim();
            tab.title = trimmed || defaultTabTitle(nextTabNumber - 1);
            tab.userRenamed = Boolean(trimmed);
        }
        renamingTabId = null;
        renameDraft = "";
    }

    export function cancelRename() {
        renamingTabId = null;
        renameDraft = "";
    }

    function onTabLabelTouchEnd(tab: MapTab, event: TouchEvent) {
        const now = Date.now();
        if (lastLabelTap.tabId === tab.id && now - lastLabelTap.time <= DOUBLE_TAP_MS) {
            lastLabelTap = { tabId: null, time: 0 };
            startRename(tab.id);
            event.preventDefault();
            return;
        }
        lastLabelTap = { tabId: tab.id, time: now };
    }

    export function selectTab(tabId: number) {
        if (renamingTabId != null) {
            commitRename();
        }
        if (activeTabId === tabId) {
            return;
        }
        activeTabId = tabId;
    }

    export function closeTab(tabId: number) {
        if (renamingTabId === tabId) {
            cancelRename();
        }
        const index = tabs.findIndex((tab) => tab.id === tabId);
        if (index === -1) return;

        const closing = tabs[index];
        const wasActive = closing.id === activeTabId;
        tabs.splice(index, 1);

        if (tabs.length === 0) {
            addTab();
            return;
        }
        if (wasActive) {
            const neighbour = tabs[index] || tabs[index - 1] || tabs[0];
            activeTabId = neighbour.id;
        }
    }

    export function selectRelativeTab(offset: number) {
        if (tabs.length < 2) return;
        const index = tabs.findIndex((tab) => tab.id === activeTabId);
        if (index === -1) return;
        const nextIndex = (index + offset + tabs.length) % tabs.length;
        selectTab(tabs[nextIndex].id);
    }

    export function selectTabByIndex(index: number) {
        if (index >= 0 && index < tabs.length) {
            selectTab(tabs[index].id);
        }
    }

    function handleKeydown(event: KeyboardEvent) {
        if (!isWideViewport) return;

        const isMac = typeof navigator !== "undefined" && navigator.platform.toUpperCase().indexOf("MAC") >= 0;
        const mod = isMac ? event.metaKey : event.ctrlKey;
        const hasModifier = event.ctrlKey || event.metaKey || event.altKey;
        const target = document.activeElement as HTMLElement | null;
        const isInput = target && (["INPUT", "TEXTAREA"].includes(target.tagName) || target.isContentEditable);
        if (isInput && !hasModifier) return;

        const key = event.key.toLowerCase();
        if (mod && key === "t") {
            event.preventDefault();
            event.stopPropagation();
            if (canAddTab) addTab();
            return;
        }
        if (mod && key === "w") {
            event.preventDefault();
            event.stopPropagation();
            if (activeTabId != null) closeTab(activeTabId);
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

    async function migrateLegacyMapState(storageId: string) {
        try {
            const identityHash = (GlobalState.config as any)?.identity_hash || null;
            const tabKey = mapViewStateKey(identityHash, storageId);
            const existing = await TileCache.getMapState(tabKey);
            if (existing) return;
            const unscopedTab = await TileCache.getMapState(legacyMapTabStateKey(storageId));
            if (unscopedTab) {
                await TileCache.setMapState(tabKey, unscopedTab);
                return;
            }
            const legacy = await TileCache.getMapState(LEGACY_MAP_STATE_KEY);
            if (!legacy) return;
            await TileCache.setMapState(tabKey, legacy);
        } catch {
            // migration is best effort
        }
    }

    export async function restoreTabs(): Promise<boolean> {
        const saved = loadMapTabs();
        if (!saved || !saved.tabs || saved.tabs.length === 0) {
            return false;
        }
        let maxTabNumber = 0;
        tabs = saved.tabs.slice(0, MAX_MAP_TABS).map((tab: any, index: number) => {
            const tabNumber = Number.isInteger(tab.tabNumber) && tab.tabNumber > 0 ? tab.tabNumber : index + 1;
            maxTabNumber = Math.max(maxTabNumber, tabNumber);
            return {
                id: nextTabId++,
                storageId: typeof tab.storageId === "string" && tab.storageId ? tab.storageId : createStorageId(),
                title: typeof tab.title === "string" && tab.title ? tab.title : defaultTabTitle(tabNumber),
                userRenamed: tab.userRenamed === true,
                tabNumber,
            };
        });

        if (tabs.length === 0) return false;

        nextTabNumber = maxTabNumber + 1;
        const activeIndex =
            Number.isInteger(saved.activeIndex) && saved.activeIndex >= 0 && saved.activeIndex < tabs.length
                ? saved.activeIndex
                : 0;
        activeTabId = tabs[activeIndex].id;
        await migrateLegacyMapState(tabs[0].storageId);
        return true;
    }

    function persistTabs() {
        const activeIndex = tabs.findIndex((tab) => tab.id === activeTabId);
        saveMapTabs({
            tabs: tabs.map((tab) => ({
                storageId: tab.storageId,
                title: tab.title || null,
                userRenamed: tab.userRenamed === true,
                tabNumber: tab.tabNumber || null,
            })),
            activeIndex: activeIndex < 0 ? 0 : activeIndex,
        });
    }

    function onIdentitySwitched() {
        tabs = [];
        activeTabId = null;
        saveMapTabs({ tabs: [], activeIndex: 0 });
        const storageId = createStorageId();
        void addTab(null, true, storageId);
    }

    function setupViewportWatcher() {
        if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
            isWideViewport = false;
            return;
        }
        mediaQuery = window.matchMedia("(min-width: 768px)");
        isWideViewport = mediaQuery.matches;
        mediaQueryListener = (event: MediaQueryListEvent) => {
            isWideViewport = event.matches;
        };
        if (typeof mediaQuery.addEventListener === "function") {
            mediaQuery.addEventListener("change", mediaQueryListener);
        } else if (typeof (mediaQuery as any).addListener === "function") {
            (mediaQuery as any).addListener(mediaQueryListener);
        }
    }

    function teardownViewportWatcher() {
        if (!mediaQuery || !mediaQueryListener) return;
        if (typeof mediaQuery.removeEventListener === "function") {
            mediaQuery.removeEventListener("change", mediaQueryListener);
        } else if (typeof (mediaQuery as any).removeListener === "function") {
            (mediaQuery as any).removeListener(mediaQueryListener);
        }
        mediaQuery = null;
        mediaQueryListener = null;
    }

    onMount(async () => {
        setupViewportWatcher();
        window.addEventListener("keydown", handleKeydown, true);
        GlobalEmitter.on("identity-switched", onIdentitySwitched);

        if (!(await restoreTabs())) {
            const storageId = createStorageId();
            await migrateLegacyMapState(storageId);
            addTab(null, true, storageId);
        }
    });

    onDestroy(() => {
        GlobalEmitter.off("identity-switched", onIdentitySwitched);
        teardownViewportWatcher();
        window.removeEventListener("keydown", handleKeydown, true);
    });
</script>

<div class="flex flex-1 min-w-0 h-full flex-col overflow-hidden bg-sem-canvas text-sem-fg">
    {#if showTabStrip}
        <MapTabBar
            {tabs}
            {activeTabId}
            {renamingTabId}
            bind:renameDraft
            {canAddTab}
            bind:renameInputEl
            {tabTitle}
            onselect={selectTab}
            onstartrename={startRename}
            oncommitrename={commitRename}
            oncancelrename={cancelRename}
            ontablabeltouchend={onTabLabelTouchEnd}
            onclosetab={closeTab}
            onaddtab={() => addTab()}
        />
    {/if}

    <div class="flex flex-1 min-h-0 min-w-0 overflow-hidden">
        {#each tabs as tab (tab.storageId)}
            <div class="flex-1 min-h-0 min-w-0 {tab.id === activeTabId ? 'flex' : 'hidden'}">
                <MapPage
                    embedded={true}
                    tabStorageId={tab.storageId}
                    tabTitle={tabTitle(tab)}
                    isActiveTab={tab.id === activeTabId && isRouteActive}
                    onUpdateTitle={(title) => onMapUpdateTitle(tab.id, title)}
                />
            </div>
        {/each}
    </div>
</div>
