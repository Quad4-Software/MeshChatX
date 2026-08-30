<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div class="flex flex-1 min-w-0 h-full flex-col overflow-hidden bg-sem-canvas text-sem-fg">
        <div
            v-if="showTabStrip"
            class="nomad-tab-strip flex h-8 min-[900px]:h-9 shrink-0 flex-nowrap items-stretch overflow-x-auto overflow-y-hidden border-b border-sem-border bg-sem-surface-muted px-1 pt-0.5"
            role="tablist"
        >
            <button
                v-for="(tab, tabIndex) in tabs"
                :key="tab.id"
                type="button"
                role="tab"
                draggable="true"
                :aria-selected="tab.id === activeTabId"
                class="group flex min-h-0 min-w-[6.5rem] max-w-[12rem] min-[900px]:min-w-[7rem] min-[900px]:max-w-[14rem] shrink-0 cursor-grab items-center gap-1 border border-transparent px-2 min-[900px]:px-3 text-xs min-[900px]:text-sm leading-none transition-[opacity,background-color,border-color] duration-150 rounded-t-lg active:cursor-grabbing"
                :class="[
                    tab.private
                        ? tab.id === activeTabId
                            ? 'border-purple-500/60 border-b-transparent bg-[#2b1065] font-medium text-purple-100'
                            : 'text-purple-300/90 hover:bg-purple-900/40'
                        : tab.id === activeTabId
                          ? 'border-sem-border border-b-transparent bg-sem-canvas font-medium text-sem-fg'
                          : 'text-sem-fg-muted hover:bg-sem-surface/50',
                    dragTabIndex === tabIndex ? 'opacity-50' : '',
                ]"
                :title="tab.private ? $t('nomadnet.private_tab') : undefined"
                @click="selectTab(tab.id)"
                @dragstart="onTabDragStart(tabIndex, $event)"
                @dragover.prevent="onTabDragOver(tabIndex)"
                @drop.prevent="onTabDrop(tabIndex)"
                @dragend="onTabDragEnd"
                @contextmenu.prevent="openTabContextMenu($event, tab)"
            >
                <MaterialDesignIcon
                    v-if="tab.private"
                    icon-name="incognito"
                    class="size-3.5 min-[900px]:size-4 shrink-0 text-purple-300"
                />
                <span class="min-w-0 flex-1 truncate text-left leading-none">{{ tabTitle(tab) }}</span>
                <span
                    class="shrink-0 rounded p-0.5 text-sem-fg-muted opacity-0 transition-opacity hover:bg-sem-surface hover:text-sem-fg group-hover:opacity-100 group-focus-within:opacity-100"
                    :class="tab.private ? 'hover:bg-purple-800/60 hover:text-purple-100' : ''"
                    :title="$t('common.cancel')"
                    draggable="false"
                    @click.stop="closeTab(tab.id)"
                >
                    <MaterialDesignIcon icon-name="close" class="size-3.5 min-[900px]:size-4" />
                </span>
            </button>
            <button
                type="button"
                class="mb-0 flex h-full w-8 min-[900px]:w-9 shrink-0 items-center justify-center rounded-lg text-sem-fg-muted transition-colors hover:bg-sem-surface/80"
                :title="$t('nomadnet.new_tab_shortcut')"
                @click="addTab()"
            >
                <MaterialDesignIcon icon-name="plus" class="size-4 min-[900px]:size-5" />
            </button>
            <button
                type="button"
                class="mb-0 flex h-full w-8 min-[900px]:w-9 shrink-0 items-center justify-center rounded-lg text-purple-400 transition-colors hover:bg-purple-900/40 hover:text-purple-200"
                :title="$t('nomadnet.new_private_tab_shortcut')"
                @click="addTab('', null, null, true, true)"
            >
                <MaterialDesignIcon icon-name="incognito" class="size-4 min-[900px]:size-5" />
            </button>
        </div>

        <div class="relative flex flex-1 min-h-0 min-w-0 overflow-hidden">
            <template v-for="tab in tabs" :key="tab.id">
                <NomadNetworkPage
                    v-if="isTabMounted(tab.id)"
                    v-show="tab.id === activeTabId"
                    :ref="(el) => setPageRef(tab.id, el)"
                    class="absolute inset-0 flex min-h-0 min-w-0"
                    embedded
                    :tabs-enabled="tabsEnabled"
                    :is-active="tab.id === activeTabId && isRouteActive"
                    :is-private="Boolean(tab.private)"
                    :destination-hash="tab.destinationHash"
                    :initial-path="tab.initialPath"
                    @navigate="onTabNavigate(tab.id, $event)"
                    @open-node="onOpenNode"
                    @close-tab="closeTab(tab.id)"
                />
            </template>
        </div>

        <NomadBrowserContextMenu
            :show="contextMenu.show"
            :x="contextMenu.x"
            :y="contextMenu.y"
            :just-opened="contextMenu.justOpened"
            :has-active-page="contextMenuHasActivePage"
            :can-favourite="contextMenuCanFavourite"
            :is-favourite="contextMenuIsFavourite"
            :can-download-page="contextMenuCanDownloadPage"
            :show-tab-actions="showTabStrip"
            :can-close-tabs-right="contextMenuCanCloseTabsRight"
            :can-close-other-tabs="contextMenuCanCloseOtherTabs"
            :can-close-all-tabs="tabs.length > 1"
            :context-tab-is-private="Boolean(contextMenuTab?.private)"
            @close="closeContextMenu"
            @view-source="onContextViewSource"
            @reload="onContextReload"
            @favorite="onContextFavorite"
            @download-page="onContextDownloadPage"
            @new-private-tab="onContextNewPrivateTab"
            @close-tabs-right="onContextCloseTabsRight"
            @close-other-tabs="onContextCloseOtherTabs"
            @close-all-tabs="onContextCloseAllTabs"
        />
    </div>
</template>

<script>
import NomadNetworkPage from "./NomadNetworkPage.vue";
import NomadBrowserContextMenu from "./NomadBrowserContextMenu.vue";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import GlobalState from "../../js/GlobalState";
import GlobalEmitter from "../../js/GlobalEmitter";
import { loadNomadTabs, saveNomadTabs } from "../../js/browserLayoutStore";
import LinkUtils from "../../js/LinkUtils";
import ToastUtils from "../../js/ToastUtils";

export default {
    name: "NomadNetworkBrowser",
    components: {
        NomadNetworkPage,
        NomadBrowserContextMenu,
        MaterialDesignIcon,
    },
    provide() {
        return {
            nomadBrowserTabActions: {
                openContextMenu: this.openPageContextMenu,
                closeContextMenu: this.closeContextMenu,
                getContextTabId: () => this.contextMenu.tabId ?? this.activeTabId,
            },
        };
    },
    props: {
        destinationHash: {
            type: String,
            required: false,
            default: "",
        },
    },
    data() {
        return {
            GlobalState,
            tabs: [],
            activeTabId: null,
            nextTabId: 1,
            isWideViewport: false,
            mediaQuery: null,
            mediaQueryListener: null,
            dragTabIndex: null,
            pageRefs: {},
            mountedTabIds: {},
            contextMenu: {
                show: false,
                justOpened: false,
                x: 0,
                y: 0,
                tabId: null,
            },
            isRouteActive: true,
        };
    },
    computed: {
        tabsEnabled() {
            return GlobalState.config?.nomad_tabs_enabled !== false;
        },
        showTabStrip() {
            return this.isWideViewport && this.tabsEnabled && this.tabs.length > 0;
        },
        activeTab() {
            return this.tabs.find((tab) => tab.id === this.activeTabId) || null;
        },
        tabLayoutSignature() {
            const tabs = this.tabs
                .filter((tab) => !tab.private)
                .map((tab) => `${tab.destinationHash || ""}|${tab.path || ""}|${tab.title || ""}`)
                .join("\u241f");
            const persistable = this.tabs.filter((tab) => !tab.private);
            const activeIndex = persistable.findIndex((tab) => tab.id === this.activeTabId);
            return `${activeIndex}\u241e${tabs}`;
        },
        contextTabIndex() {
            const tabId = this.contextMenu.tabId ?? this.activeTabId;
            return this.tabs.findIndex((tab) => tab.id === tabId);
        },
        contextMenuTab() {
            const tabId = this.contextMenu.tabId ?? this.activeTabId;
            return this.tabs.find((tab) => tab.id === tabId) || null;
        },
        contextPageRef() {
            const tabId = this.contextMenu.tabId ?? this.activeTabId;
            return tabId != null ? this.pageRefs[tabId] || null : null;
        },
        contextMenuHasActivePage() {
            const page = this.contextPageRef;
            return Boolean(page?.selectedNode && page?.nodePagePath);
        },
        contextMenuCanFavourite() {
            if (this.contextMenuTab?.private) {
                return false;
            }
            return Boolean(this.contextPageRef?.selectedNode?.destination_hash);
        },
        contextMenuIsFavourite() {
            const page = this.contextPageRef;
            const hash = page?.selectedNode?.destination_hash;
            return hash ? page.isFavourite(hash) : false;
        },
        contextMenuCanDownloadPage() {
            const page = this.contextPageRef;
            return Boolean(
                page?.nodePageContent && page?.nodePagePath && !page?.isFailedPageContent?.(page.nodePageContent)
            );
        },
        contextMenuCanCloseTabsRight() {
            return this.contextTabIndex >= 0 && this.contextTabIndex < this.tabs.length - 1;
        },
        contextMenuCanCloseOtherTabs() {
            return this.tabs.length > 1 && this.contextTabIndex >= 0;
        },
    },
    watch: {
        tabLayoutSignature() {
            this.persistTabs();
        },
        $route(to) {
            this.applyIncomingNomadRoute(to);
        },
    },
    mounted() {
        this.setupViewportWatcher();
        window.addEventListener("keydown", this.handleKeydown, true);

        const initialHash = (this.destinationHash || this.$route?.params?.destinationHash || "").trim();
        const initialPath = this.$route?.query?.path || null;
        const forceNewTab = this.$route?.query?.newTab === "1";

        if (!this.restoreTabs(initialHash, initialPath, forceNewTab)) {
            this.addTab(initialHash, initialPath);
        }
        if (forceNewTab) {
            this.clearNewTabQuery();
        }

        GlobalEmitter.on("nomad-open-node", this.handleNomadOpenNode);
        GlobalEmitter.on("identity-switched", this.onIdentitySwitched);
        this.mountTab(this.activeTabId);
    },
    activated() {
        this.isRouteActive = true;
        this.applyIncomingNomadRoute(this.$route);
    },
    deactivated() {
        this.isRouteActive = false;
    },
    beforeUnmount() {
        GlobalEmitter.off("nomad-open-node", this.handleNomadOpenNode);
        GlobalEmitter.off("identity-switched", this.onIdentitySwitched);
        this.teardownViewportWatcher();
        window.removeEventListener("keydown", this.handleKeydown, true);
    },
    methods: {
        applyIncomingNomadRoute(route) {
            if (route?.name !== "nomadnetwork") {
                return;
            }
            if (route.query?.newTab === "1") {
                this.consumeNewTabRouteQuery(route);
                return;
            }
            const destinationHash = (route.params?.destinationHash || this.destinationHash || "").trim();
            if (!destinationHash) {
                return;
            }
            const activeHash = (this.activeTab?.destinationHash || "").trim();
            if (destinationHash === activeHash) {
                return;
            }
            this.onOpenNode({
                destinationHash,
                pagePath: route.query?.path || null,
                activate: true,
            });
        },
        onIdentitySwitched() {
            this.tabs = [];
            this.activeTabId = null;
            this.pageRefs = {};
            this.mountedTabIds = {};
            this.addTab();
            saveNomadTabs({ tabs: [], activeIndex: 0 });
        },
        setupViewportWatcher() {
            if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
                this.isWideViewport = false;
                return;
            }
            this.mediaQuery = window.matchMedia("(min-width: 768px)");
            this.isWideViewport = this.mediaQuery.matches;
            this.mediaQueryListener = (event) => {
                this.isWideViewport = event.matches;
            };
            if (typeof this.mediaQuery.addEventListener === "function") {
                this.mediaQuery.addEventListener("change", this.mediaQueryListener);
            } else if (typeof this.mediaQuery.addListener === "function") {
                this.mediaQuery.addListener(this.mediaQueryListener);
            }
        },
        teardownViewportWatcher() {
            if (!this.mediaQuery || !this.mediaQueryListener) {
                return;
            }
            if (typeof this.mediaQuery.removeEventListener === "function") {
                this.mediaQuery.removeEventListener("change", this.mediaQueryListener);
            } else if (typeof this.mediaQuery.removeListener === "function") {
                this.mediaQuery.removeListener(this.mediaQueryListener);
            }
            this.mediaQuery = null;
            this.mediaQueryListener = null;
        },
        mountTab(tabId) {
            if (tabId == null || this.mountedTabIds[tabId]) {
                return;
            }
            this.mountedTabIds = { ...this.mountedTabIds, [tabId]: true };
        },
        isTabMounted(tabId) {
            return Boolean(this.mountedTabIds[tabId]);
        },
        unmountTab(tabId) {
            if (tabId == null || !this.mountedTabIds[tabId]) {
                return;
            }
            delete this.pageRefs[tabId];
            const nextMounted = { ...this.mountedTabIds };
            delete nextMounted[tabId];
            this.mountedTabIds = nextMounted;
        },
        addTab(destinationHash = "", initialPath = null, title = null, activate = true, isPrivate = false) {
            const id = this.nextTabId++;
            this.tabs.push({
                id,
                destinationHash: destinationHash || "",
                initialPath: initialPath || null,
                path: initialPath || null,
                title: title || null,
                private: Boolean(isPrivate),
            });
            if (activate) {
                this.activeTabId = id;
                this.mountTab(id);
                this.syncRoute();
            }
            return id;
        },
        onOpenNode(payload) {
            const destinationHash = payload?.destinationHash || "";
            const forceNewTab = payload?.forceNewTab === true;
            const openPrivate = payload?.private === true || Boolean(this.activeTab?.private);

            if (destinationHash && !forceNewTab) {
                const existing = this.tabs.find(
                    (tab) => tab.destinationHash === destinationHash && Boolean(tab.private) === openPrivate
                );
                if (existing) {
                    if (payload?.title) {
                        existing.title = payload.title;
                    }
                    if (payload?.activate !== false) {
                        this.selectTab(existing.id);
                    }
                    return;
                }
            }

            this.addTab(
                destinationHash,
                payload?.pagePath || null,
                payload?.title || null,
                payload?.activate !== false,
                openPrivate
            );
        },
        selectRelativeTab(offset) {
            if (this.tabs.length < 2) {
                return;
            }
            const index = this.tabs.findIndex((tab) => tab.id === this.activeTabId);
            if (index === -1) {
                return;
            }
            const nextIndex = (index + offset + this.tabs.length) % this.tabs.length;
            this.selectTab(this.tabs[nextIndex].id);
        },
        selectTabByIndex(index) {
            if (index >= 0 && index < this.tabs.length) {
                this.selectTab(this.tabs[index].id);
            }
        },
        handleKeydown(event) {
            if (!this.tabsEnabled || this.$route?.name !== "nomadnetwork") {
                return;
            }

            const isMac = navigator.platform.toUpperCase().indexOf("MAC") >= 0;
            const mod = isMac ? event.metaKey : event.ctrlKey;
            const hasModifier = event.ctrlKey || event.metaKey || event.altKey;
            const isInput =
                ["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName) ||
                document.activeElement?.isContentEditable;
            if (isInput && !hasModifier) {
                return;
            }

            const key = event.key.toLowerCase();

            if (mod && key === "t") {
                event.preventDefault();
                event.stopPropagation();
                this.addTab();
                return;
            }
            if (mod && event.shiftKey && key === "p") {
                event.preventDefault();
                event.stopPropagation();
                this.addTab("", null, null, true, true);
                return;
            }
            if (mod && key === "w") {
                event.preventDefault();
                event.stopPropagation();
                if (this.activeTabId != null) {
                    this.closeTab(this.activeTabId);
                }
                return;
            }
            if (event.ctrlKey && key === "tab") {
                event.preventDefault();
                event.stopPropagation();
                this.selectRelativeTab(event.shiftKey ? -1 : 1);
                return;
            }
            if (event.ctrlKey && key === "pageup") {
                event.preventDefault();
                event.stopPropagation();
                this.selectRelativeTab(-1);
                return;
            }
            if (event.ctrlKey && key === "pagedown") {
                event.preventDefault();
                event.stopPropagation();
                this.selectRelativeTab(1);
                return;
            }
            if (mod && key >= "1" && key <= "9") {
                event.preventDefault();
                event.stopPropagation();
                this.selectTabByIndex(parseInt(key, 10) - 1);
            }
        },
        restoreTabs(routeHash, routePath, forceNewTab = false) {
            const saved = loadNomadTabs();
            if (!saved || saved.tabs.length === 0) {
                return false;
            }

            this.tabs = saved.tabs
                .map((tab) => ({
                    id: this.nextTabId++,
                    destinationHash:
                        typeof tab.destinationHash === "string" && /^[0-9a-fA-F]{32}$/.test(tab.destinationHash)
                            ? tab.destinationHash
                            : "",
                    initialPath: this.sanitizeNomadTabPath(tab.path),
                    path: this.sanitizeNomadTabPath(tab.path),
                    title: typeof tab.title === "string" ? tab.title : null,
                    private: false,
                }))
                .filter((tab) => !this.isExternalNomadTabPath(tab.path));

            if (this.tabs.length === 0) {
                return false;
            }

            const activeIndex =
                Number.isInteger(saved.activeIndex) && saved.activeIndex >= 0 && saved.activeIndex < this.tabs.length
                    ? saved.activeIndex
                    : 0;
            this.activeTabId = this.tabs[activeIndex].id;

            if (routeHash) {
                if (forceNewTab) {
                    this.addTab(routeHash, routePath);
                } else {
                    const existing = this.tabs.find((tab) => tab.destinationHash === routeHash);
                    if (existing) {
                        this.activeTabId = existing.id;
                    } else {
                        this.addTab(routeHash, routePath);
                    }
                }
            }

            this.syncRoute();
            return true;
        },
        sanitizeNomadTabPath(path) {
            if (typeof path !== "string" || path.length === 0) {
                return null;
            }
            if (LinkUtils.httpUrlHrefOrNull(path.trim())) {
                return null;
            }
            return path;
        },
        isExternalNomadTabPath(path) {
            return typeof path === "string" && LinkUtils.httpUrlHrefOrNull(path.trim()) != null;
        },
        persistTabs() {
            const persistable = this.tabs.filter((tab) => !tab.private);
            if (persistable.length === 0) {
                saveNomadTabs({ tabs: [], activeIndex: 0 });
                return;
            }
            let activeIndex = persistable.findIndex((tab) => tab.id === this.activeTabId);
            if (activeIndex < 0) {
                activeIndex = 0;
            }
            saveNomadTabs({
                tabs: persistable.map((tab) => ({
                    destinationHash: tab.destinationHash || "",
                    path: this.sanitizeNomadTabPath(tab.path),
                    title: tab.title || null,
                })),
                activeIndex,
            });
        },
        selectTab(tabId) {
            if (this.activeTabId === tabId) {
                return;
            }
            const tab = this.tabs.find((entry) => entry.id === tabId);
            if (!tab) {
                ToastUtils.warning(this.$t("nomadnet.tab_switch_failed"));
                return;
            }
            this.activeTabId = tabId;
            this.mountTab(tabId);
            this.syncRoute();
            this.$nextTick(() => {
                this.verifyActiveTabPage(tab);
            });
        },
        verifyActiveTabPage(tab) {
            const page = this.pageRefs[tab.id];
            if (!page || typeof page.getEmbeddedTabStateHash !== "function") {
                return;
            }
            const expectedHash = (tab.destinationHash || "").trim();
            const loadedHash = page.getEmbeddedTabStateHash();
            if (!expectedHash || !loadedHash || expectedHash === loadedHash) {
                return;
            }
            if (typeof page.restoreEmbeddedTabState === "function") {
                page.restoreEmbeddedTabState(expectedHash, tab.path);
            }
            ToastUtils.warning(this.$t("nomadnet.tab_content_mismatch"));
        },
        onTabDragStart(index, event) {
            this.dragTabIndex = index;
            if (event.dataTransfer) {
                event.dataTransfer.effectAllowed = "move";
                event.dataTransfer.setData("text/plain", String(index));
            }
        },
        onTabDragOver(index) {
            if (this.dragTabIndex === null || this.dragTabIndex === index) {
                return;
            }
            const [moved] = this.tabs.splice(this.dragTabIndex, 1);
            this.tabs.splice(index, 0, moved);
            this.dragTabIndex = index;
        },
        onTabDrop() {
            this.dragTabIndex = null;
            this.persistTabs();
        },
        onTabDragEnd() {
            this.dragTabIndex = null;
        },
        closeTab(tabId) {
            const index = this.tabs.findIndex((tab) => tab.id === tabId);
            if (index === -1) {
                return;
            }

            const wasActive = this.tabs[index].id === this.activeTabId;
            this.tabs.splice(index, 1);
            this.unmountTab(tabId);

            if (this.tabs.length === 0) {
                this.addTab();
                return;
            }

            if (wasActive) {
                const neighbour = this.tabs[index] || this.tabs[index - 1] || this.tabs[0];
                this.activeTabId = neighbour.id;
                this.mountTab(neighbour.id);
            }
            this.syncRoute();
        },
        onTabNavigate(tabId, payload) {
            const tab = this.tabs.find((entry) => entry.id === tabId);
            if (!tab) {
                return;
            }
            if (payload?.destinationHash != null) {
                tab.destinationHash = payload.destinationHash;
            }
            if (payload?.pagePath != null) {
                tab.path = payload.pagePath;
            }
            if (payload?.title != null) {
                tab.title = payload.title;
            }
            if (tab.id === this.activeTabId) {
                this.syncRoute();
            }
        },
        tabTitle(tab) {
            if (tab.title) {
                return tab.title;
            }
            if (tab.destinationHash) {
                return tab.destinationHash.slice(0, 12);
            }
            return tab.private ? this.$t("nomadnet.private_tab") : this.$t("nomadnet.new_tab");
        },
        onContextNewPrivateTab() {
            this.closeContextMenu();
            this.addTab("", null, null, true, true);
        },
        syncRoute() {
            const tab = this.activeTab;
            const targetHash = tab?.destinationHash || "";
            const currentHash = this.$route?.params?.destinationHash || "";
            if (targetHash === currentHash) {
                return;
            }
            const routeOptions = {
                name: "nomadnetwork",
                params: { destinationHash: targetHash },
            };
            if (this.$route?.query) {
                routeOptions.query = { ...this.$route.query };
                delete routeOptions.query.path;
                delete routeOptions.query.archive_id;
                delete routeOptions.query.newTab;
            }
            this.$router.replace(routeOptions).catch(() => {});
        },
        handleNomadOpenNode(payload) {
            const destinationHash = (payload?.destinationHash || "").trim();
            if (!destinationHash) {
                return;
            }
            try {
                if (this.$route?.name !== "nomadnetwork") {
                    this.$router
                        .push({
                            name: "nomadnetwork",
                            params: { destinationHash },
                            query: { newTab: "1" },
                        })
                        .then(() => {
                            this.consumeNewTabRouteQuery(this.$route);
                        })
                        .catch(() => {
                            ToastUtils.error(this.$t("nomadnet.open_node_failed"));
                        });
                    return;
                }
                this.onOpenNode({
                    ...payload,
                    destinationHash,
                    forceNewTab: payload?.forceNewTab !== false,
                });
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("nomadnet.open_node_failed"));
            }
        },
        consumeNewTabRouteQuery(route) {
            if (route?.name !== "nomadnetwork" || route.query?.newTab !== "1") {
                return;
            }
            const destinationHash = (route.params?.destinationHash || "").trim();
            if (!destinationHash) {
                return;
            }
            this.clearNewTabQuery();
            this.onOpenNode({
                destinationHash,
                pagePath: route.query?.path || null,
                forceNewTab: true,
            });
        },
        clearNewTabQuery() {
            if (this.$route?.query?.newTab !== "1") {
                return;
            }
            const query = { ...this.$route.query };
            delete query.newTab;
            this.$router.replace({ ...this.$route, query }).catch(() => {});
        },
        setPageRef(tabId, el) {
            if (el) {
                this.pageRefs[tabId] = el;
                return;
            }
            delete this.pageRefs[tabId];
        },
        openTabContextMenu(event, tab) {
            this.selectTab(tab.id);
            this.contextMenu = {
                show: true,
                justOpened: true,
                x: event.clientX,
                y: event.clientY,
                tabId: tab.id,
            };
            setTimeout(() => {
                this.contextMenu.justOpened = false;
            }, 50);
        },
        openPageContextMenu(event) {
            this.contextMenu = {
                show: true,
                justOpened: true,
                x: event.clientX,
                y: event.clientY,
                tabId: this.activeTabId,
            };
            setTimeout(() => {
                this.contextMenu.justOpened = false;
            }, 50);
        },
        closeContextMenu() {
            this.contextMenu.show = false;
        },
        async runContextPageAction(actionFn) {
            const page = this.contextPageRef;
            if (!page) {
                ToastUtils.warning(this.$t("nomadnet.context_menu_page_unavailable"));
                this.closeContextMenu();
                return;
            }
            try {
                await actionFn(page);
            } catch (error) {
                console.error("nomad browser context menu action failed", error);
                ToastUtils.error(this.$t("nomadnet.context_menu_action_failed"));
            } finally {
                this.closeContextMenu();
            }
        },
        onContextViewSource() {
            this.runContextPageAction((page) => page.showPageSource());
        },
        onContextReload() {
            this.runContextPageAction((page) => page.reloadNodePage());
        },
        onContextFavorite() {
            this.runContextPageAction((page) => page.toggleFavouriteFromContext());
        },
        onContextDownloadPage() {
            this.runContextPageAction((page) => page.downloadPageToDisk());
        },
        onContextCloseTabsRight() {
            const tabId = this.contextMenu.tabId ?? this.activeTabId;
            this.closeTabsToRight(tabId);
            this.closeContextMenu();
        },
        onContextCloseOtherTabs() {
            const tabId = this.contextMenu.tabId ?? this.activeTabId;
            this.closeOtherTabs(tabId);
            this.closeContextMenu();
        },
        onContextCloseAllTabs() {
            this.closeAllTabs();
            this.closeContextMenu();
        },
        closeTabsToRight(tabId) {
            const index = this.tabs.findIndex((tab) => tab.id === tabId);
            if (index === -1) {
                return;
            }
            const removeIds = this.tabs.slice(index + 1).map((tab) => tab.id);
            removeIds.forEach((id) => this.closeTab(id));
        },
        closeOtherTabs(tabId) {
            const keepId = tabId;
            const removeIds = this.tabs.filter((tab) => tab.id !== keepId).map((tab) => tab.id);
            removeIds.forEach((id) => this.closeTab(id));
            this.selectTab(keepId);
        },
        closeAllTabs() {
            this.tabs = [];
            this.pageRefs = {};
            this.addTab();
        },
    },
};
</script>

<style scoped>
.nomad-tab-strip {
    scrollbar-width: thin;
    scrollbar-color: transparent transparent;
}

@media (max-height: 700px) {
    .nomad-tab-strip {
        height: 1.875rem;
        padding-top: 2px;
    }
}

.nomad-tab-strip::-webkit-scrollbar {
    height: 6px;
}

.nomad-tab-strip::-webkit-scrollbar:vertical {
    display: none;
    width: 0;
}

.nomad-tab-strip::-webkit-scrollbar-thumb {
    border-radius: 999px;
    background: color-mix(in srgb, var(--mc-border, #27272a) 70%, transparent);
}
</style>
