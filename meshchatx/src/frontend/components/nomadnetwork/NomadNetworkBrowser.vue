<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div class="flex flex-1 min-w-0 h-full flex-col overflow-hidden">
        <div
            v-if="showTabStrip"
            class="flex items-stretch h-9 shrink-0 border-b border-gray-200 dark:border-zinc-800 bg-gray-50 dark:bg-zinc-900 overflow-x-auto"
            role="tablist"
        >
            <button
                v-for="tab in tabs"
                :key="tab.id"
                type="button"
                role="tab"
                :aria-selected="tab.id === activeTabId"
                class="group flex items-center gap-1.5 min-w-[8rem] max-w-[14rem] px-3 border-r border-gray-200 dark:border-zinc-800 text-sm transition-colors"
                :class="
                    tab.id === activeTabId
                        ? 'bg-white dark:bg-zinc-950 text-gray-900 dark:text-gray-100'
                        : 'text-gray-500 dark:text-zinc-400 hover:bg-gray-100 dark:hover:bg-zinc-800'
                "
                @click="selectTab(tab.id)"
            >
                <MaterialDesignIcon icon-name="earth" class="size-4 shrink-0 opacity-70" />
                <span class="truncate flex-1 text-left">{{ tabTitle(tab) }}</span>
                <span
                    class="shrink-0 rounded p-0.5 text-gray-400 hover:bg-gray-200 hover:text-gray-700 dark:hover:bg-zinc-700 dark:hover:text-gray-200"
                    :title="$t('common.cancel')"
                    @click.stop="closeTab(tab.id)"
                >
                    <MaterialDesignIcon icon-name="close" class="size-3.5" />
                </span>
            </button>
            <button
                type="button"
                class="flex items-center justify-center w-9 shrink-0 text-gray-500 dark:text-zinc-400 hover:bg-gray-100 dark:hover:bg-zinc-800 transition-colors"
                :title="$t('nomadnet.new_tab_shortcut')"
                @click="addTab()"
            >
                <MaterialDesignIcon icon-name="plus" class="size-5" />
            </button>
        </div>

        <div class="flex flex-1 min-h-0 min-w-0 overflow-hidden">
            <NomadNetworkPage
                v-for="tab in tabs"
                v-show="tab.id === activeTabId"
                :key="tab.id"
                embedded
                :tabs-enabled="tabsEnabled"
                :destination-hash="tab.destinationHash"
                :initial-path="tab.initialPath"
                @navigate="onTabNavigate(tab.id, $event)"
                @open-node="onOpenNode"
                @close-tab="closeTab(tab.id)"
            />
        </div>
    </div>
</template>

<script>
import NomadNetworkPage from "./NomadNetworkPage.vue";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import GlobalState from "../../js/GlobalState";
import { loadNomadTabs, saveNomadTabs } from "../../js/browserLayoutStore";

export default {
    name: "NomadNetworkBrowser",
    components: {
        NomadNetworkPage,
        MaterialDesignIcon,
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
                .map((tab) => `${tab.destinationHash || ""}|${tab.path || ""}|${tab.title || ""}`)
                .join("\u241f");
            const activeIndex = this.tabs.findIndex((tab) => tab.id === this.activeTabId);
            return `${activeIndex}\u241e${tabs}`;
        },
    },
    watch: {
        tabLayoutSignature() {
            this.persistTabs();
        },
    },
    mounted() {
        this.setupViewportWatcher();
        window.addEventListener("keydown", this.handleKeydown, true);

        const initialHash = (this.destinationHash || this.$route?.params?.destinationHash || "").trim();
        const initialPath = this.$route?.query?.path || null;

        if (!this.restoreTabs(initialHash, initialPath)) {
            this.addTab(initialHash, initialPath);
        }
    },
    beforeUnmount() {
        this.teardownViewportWatcher();
        window.removeEventListener("keydown", this.handleKeydown, true);
    },
    methods: {
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
        addTab(destinationHash = "", initialPath = null, title = null, activate = true) {
            const id = this.nextTabId++;
            this.tabs.push({
                id,
                destinationHash: destinationHash || "",
                initialPath: initialPath || null,
                path: initialPath || null,
                title: title || null,
            });
            if (activate) {
                this.activeTabId = id;
                this.syncRoute();
            }
            return id;
        },
        onOpenNode(payload) {
            this.addTab(
                payload?.destinationHash || "",
                payload?.pagePath || null,
                payload?.title || null,
                payload?.activate !== false
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
        restoreTabs(routeHash, routePath) {
            const saved = loadNomadTabs();
            if (!saved || saved.tabs.length === 0) {
                return false;
            }

            this.tabs = saved.tabs.map((tab) => ({
                id: this.nextTabId++,
                destinationHash: typeof tab.destinationHash === "string" ? tab.destinationHash : "",
                initialPath: typeof tab.path === "string" ? tab.path : null,
                path: typeof tab.path === "string" ? tab.path : null,
                title: typeof tab.title === "string" ? tab.title : null,
            }));

            const activeIndex =
                Number.isInteger(saved.activeIndex) && saved.activeIndex >= 0 && saved.activeIndex < this.tabs.length
                    ? saved.activeIndex
                    : 0;
            this.activeTabId = this.tabs[activeIndex].id;

            if (routeHash) {
                const existing = this.tabs.find((tab) => tab.destinationHash === routeHash);
                if (existing) {
                    this.activeTabId = existing.id;
                } else {
                    this.addTab(routeHash, routePath);
                }
            }

            this.syncRoute();
            return true;
        },
        persistTabs() {
            const activeIndex = this.tabs.findIndex((tab) => tab.id === this.activeTabId);
            saveNomadTabs({
                tabs: this.tabs.map((tab) => ({
                    destinationHash: tab.destinationHash || "",
                    path: tab.path || null,
                    title: tab.title || null,
                })),
                activeIndex: activeIndex < 0 ? 0 : activeIndex,
            });
        },
        selectTab(tabId) {
            if (this.activeTabId === tabId) {
                return;
            }
            this.activeTabId = tabId;
            this.syncRoute();
        },
        closeTab(tabId) {
            const index = this.tabs.findIndex((tab) => tab.id === tabId);
            if (index === -1) {
                return;
            }

            const wasActive = this.tabs[index].id === this.activeTabId;
            this.tabs.splice(index, 1);

            if (this.tabs.length === 0) {
                this.addTab();
                return;
            }

            if (wasActive) {
                const neighbour = this.tabs[index] || this.tabs[index - 1] || this.tabs[0];
                this.activeTabId = neighbour.id;
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
            return this.$t("nomadnet.new_tab");
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
            }
            this.$router.replace(routeOptions).catch(() => {});
        },
    },
};
</script>
