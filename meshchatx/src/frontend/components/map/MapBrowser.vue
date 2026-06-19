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
                <MaterialDesignIcon icon-name="map" class="size-4 shrink-0 opacity-70" />
                <input
                    v-if="renamingTabId === tab.id"
                    ref="renameInput"
                    v-model="renameDraft"
                    type="text"
                    class="flex-1 min-w-0 bg-transparent border-b border-blue-500 outline-none text-sm text-gray-900 dark:text-gray-100"
                    :maxlength="64"
                    @click.stop
                    @keydown.enter.prevent="commitRename"
                    @keydown.esc.prevent="cancelRename"
                    @blur="commitRename"
                />
                <span
                    v-else
                    class="truncate flex-1 text-left"
                    :title="$t('map.tab_rename_hint')"
                    @dblclick.stop="startRename(tab.id)"
                    @touchend.stop="onTabLabelTouchEnd(tab, $event)"
                >
                    {{ tabTitle(tab) }}
                </span>
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
                :title="$t('map.new_tab_shortcut')"
                @click="addTab()"
            >
                <MaterialDesignIcon icon-name="plus" class="size-5" />
            </button>
        </div>

        <div class="flex flex-1 min-h-0 min-w-0 overflow-hidden">
            <MapPage
                v-for="tab in tabs"
                v-show="tab.id === activeTabId"
                :key="tab.storageId"
                embedded
                :tab-storage-id="tab.storageId"
                :tab-title="tabTitle(tab)"
                :is-active-tab="tab.id === activeTabId"
                @update-title="onMapUpdateTitle(tab.id, $event)"
            />
        </div>
    </div>
</template>

<script>
import MapPage from "./MapPage.vue";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import TileCache from "../../js/TileCache";
import { loadMapTabs, saveMapTabs } from "../../js/browserLayoutStore";

const LEGACY_MAP_STATE_KEY = "last_view";
const DOUBLE_TAP_MS = 400;

function createStorageId() {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
        return crypto.randomUUID();
    }
    return `map-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export default {
    name: "MapBrowser",
    components: {
        MapPage,
        MaterialDesignIcon,
    },
    data() {
        return {
            tabs: [],
            activeTabId: null,
            nextTabId: 1,
            nextTabNumber: 1,
            isWideViewport: false,
            mediaQuery: null,
            mediaQueryListener: null,
            renamingTabId: null,
            renameDraft: "",
            lastLabelTap: { tabId: null, time: 0 },
        };
    },
    computed: {
        showTabStrip() {
            return this.tabs.length > 0;
        },
        activeTab() {
            return this.tabs.find((tab) => tab.id === this.activeTabId) || null;
        },
        tabLayoutSignature() {
            const tabs = this.tabs
                .map((tab) => `${tab.storageId || ""}|${tab.title || ""}|${tab.userRenamed ? "1" : "0"}`)
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
    async mounted() {
        this.setupViewportWatcher();
        window.addEventListener("keydown", this.handleKeydown, true);

        if (!(await this.restoreTabs())) {
            const storageId = createStorageId();
            await this.migrateLegacyMapState(storageId);
            await this.addTab(null, true, storageId);
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
        defaultTabTitle(tabNumber = this.nextTabNumber) {
            return this.$t("map.tab_default_name", { number: tabNumber });
        },
        addTab(title = null, activate = true, storageId = null) {
            const tabNumber = this.nextTabNumber++;
            const id = this.nextTabId++;
            const resolvedStorageId = storageId || createStorageId();
            this.tabs.push({
                id,
                storageId: resolvedStorageId,
                title: title || this.defaultTabTitle(tabNumber),
                userRenamed: Boolean(title),
                tabNumber,
            });
            if (activate) {
                this.activeTabId = id;
            }
            return id;
        },
        tabTitle(tab) {
            if (tab.title) {
                return tab.title;
            }
            return this.$t("map.new_tab");
        },
        onMapUpdateTitle(tabId, title) {
            const tab = this.tabs.find((entry) => entry.id === tabId);
            if (!tab || tab.userRenamed) {
                return;
            }
            const trimmed = typeof title === "string" ? title.trim() : "";
            if (!trimmed) {
                return;
            }
            tab.title = trimmed.slice(0, 64);
        },
        startRename(tabId) {
            const tab = this.tabs.find((entry) => entry.id === tabId);
            if (!tab) {
                return;
            }
            this.renamingTabId = tabId;
            this.renameDraft = this.tabTitle(tab);
            this.$nextTick(() => {
                const input = this.$refs.renameInput;
                const el = Array.isArray(input) ? input.find((node) => node) : input;
                el?.focus?.();
                el?.select?.();
            });
        },
        commitRename() {
            if (this.renamingTabId == null) {
                return;
            }
            const tab = this.tabs.find((entry) => entry.id === this.renamingTabId);
            if (tab) {
                const trimmed = this.renameDraft.trim();
                tab.title = trimmed || this.defaultTabTitle(this.nextTabNumber - 1);
                tab.userRenamed = Boolean(trimmed);
            }
            this.renamingTabId = null;
            this.renameDraft = "";
        },
        cancelRename() {
            this.renamingTabId = null;
            this.renameDraft = "";
        },
        onTabLabelTouchEnd(tab, event) {
            const now = Date.now();
            if (this.lastLabelTap.tabId === tab.id && now - this.lastLabelTap.time <= DOUBLE_TAP_MS) {
                this.lastLabelTap = { tabId: null, time: 0 };
                this.startRename(tab.id);
                event.preventDefault();
                return;
            }
            this.lastLabelTap = { tabId: tab.id, time: now };
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
            if (this.$route?.name !== "map") {
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
        async migrateLegacyMapState(storageId) {
            try {
                const legacy = await TileCache.getMapState(LEGACY_MAP_STATE_KEY);
                if (!legacy) {
                    return;
                }
                const tabKey = `map_tab_${storageId}`;
                const existing = await TileCache.getMapState(tabKey);
                if (!existing) {
                    await TileCache.setMapState(tabKey, legacy);
                }
            } catch {
                // migration is best-effort
            }
        },
        async restoreTabs() {
            const saved = loadMapTabs();
            if (!saved || saved.tabs.length === 0) {
                return false;
            }

            let maxTabNumber = 0;
            this.tabs = saved.tabs.map((tab, index) => {
                const tabNumber = Number.isInteger(tab.tabNumber) && tab.tabNumber > 0 ? tab.tabNumber : index + 1;
                maxTabNumber = Math.max(maxTabNumber, tabNumber);
                return {
                    id: this.nextTabId++,
                    storageId: typeof tab.storageId === "string" && tab.storageId ? tab.storageId : createStorageId(),
                    title: typeof tab.title === "string" && tab.title ? tab.title : this.defaultTabTitle(tabNumber),
                    userRenamed: tab.userRenamed === true,
                    tabNumber,
                };
            });

            if (this.tabs.length === 0) {
                return false;
            }

            this.nextTabNumber = maxTabNumber + 1;

            const activeIndex =
                Number.isInteger(saved.activeIndex) && saved.activeIndex >= 0 && saved.activeIndex < this.tabs.length
                    ? saved.activeIndex
                    : 0;
            this.activeTabId = this.tabs[activeIndex].id;

            await this.migrateLegacyMapState(this.tabs[0].storageId);
            return true;
        },
        persistTabs() {
            const activeIndex = this.tabs.findIndex((tab) => tab.id === this.activeTabId);
            saveMapTabs({
                tabs: this.tabs.map((tab) => ({
                    storageId: tab.storageId,
                    title: tab.title || null,
                    userRenamed: tab.userRenamed === true,
                    tabNumber: tab.tabNumber || null,
                })),
                activeIndex: activeIndex < 0 ? 0 : activeIndex,
            });
        },
        selectTab(tabId) {
            if (this.renamingTabId != null) {
                this.commitRename();
            }
            if (this.activeTabId === tabId) {
                return;
            }
            this.activeTabId = tabId;
        },
        closeTab(tabId) {
            if (this.renamingTabId === tabId) {
                this.cancelRename();
            }

            const index = this.tabs.findIndex((tab) => tab.id === tabId);
            if (index === -1) {
                return;
            }

            const closing = this.tabs[index];
            const wasActive = closing.id === this.activeTabId;
            this.tabs.splice(index, 1);

            if (this.tabs.length === 0) {
                this.addTab();
                return;
            }

            if (wasActive) {
                const neighbour = this.tabs[index] || this.tabs[index - 1] || this.tabs[0];
                this.activeTabId = neighbour.id;
            }
        },
    },
};
</script>
