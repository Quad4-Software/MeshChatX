<template>
    <div
        class="flex flex-col w-full sm:w-80 sm:min-w-80 min-h-0 bg-white/90 dark:bg-zinc-950/80 backdrop-blur border-r border-gray-200 dark:border-zinc-800"
    >
        <div class="flex">
            <button
                type="button"
                class="sidebar-tab"
                :class="{ 'sidebar-tab--active': tab === 'favourites' }"
                @click="tab = 'favourites'"
            >
                {{ $t("nomadnet.favourites") }}
            </button>
            <button
                type="button"
                class="sidebar-tab"
                :class="{ 'sidebar-tab--active': tab === 'announces' }"
                @click="tab = 'announces'"
            >
                {{ $t("nomadnet.announces") }}
            </button>
        </div>

        <div v-if="tab === 'favourites'" class="flex-1 flex flex-col min-h-0">
            <div class="p-3 border-b border-gray-200 dark:border-zinc-800">
                <input
                    v-model="favouritesSearchTerm"
                    type="text"
                    :placeholder="$t('nomadnet.search_favourites_placeholder', { count: favourites.length })"
                    class="input-field w-full rounded-none"
                />
            </div>
            <div
                class="flex items-center justify-between px-3 pt-2 text-[11px] uppercase tracking-wide text-gray-500 dark:text-gray-400"
            >
                <span class="font-semibold">Sections</span>
                <button
                    type="button"
                    class="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
                    @click="createSection"
                >
                    <MaterialDesignIcon icon-name="plus" class="size-4" />
                    <span>Add Section</span>
                </button>
            </div>
            <div class="flex-1 overflow-y-auto px-2 pb-4">
                <div v-if="favourites.length === 0" class="empty-state">
                    <MaterialDesignIcon icon-name="star-outline" class="w-8 h-8" />
                    <div class="font-semibold">{{ $t("nomadnet.no_favourites") }}</div>
                    <div class="text-sm text-gray-500 dark:text-gray-400">
                        {{ $t("nomadnet.add_nodes_from_announces") }}
                    </div>
                </div>
                <div v-else-if="hasFavouriteResults" class="space-y-3 pt-2">
                    <div
                        v-for="section in sectionsWithFavourites"
                        :key="section.id"
                        class="rounded-xl"
                        :class="[
                            dragOverSectionId === section.id
                                ? 'ring-1 ring-blue-400 dark:ring-blue-600 bg-blue-50/40 dark:bg-blue-900/10'
                                : '',
                            draggingSectionOverId === section.id
                                ? 'ring-1 ring-blue-300 dark:ring-blue-700 bg-blue-50/30 dark:bg-blue-900/5'
                                : '',
                        ]"
                        @dragover.prevent="onSectionDragOver(section.id)"
                        @dragleave="onSectionDragLeave"
                        @drop.prevent="onDropOnSection(section.id)"
                    >
                        <div
                            class="flex items-center justify-between px-2 py-1 cursor-pointer select-none"
                            draggable="true"
                            @click="toggleSectionCollapse(section.id)"
                            @contextmenu.prevent="openSectionContextMenu($event, section)"
                            @dragstart="onSectionDragStart(section.id)"
                            @dragover.prevent="onSectionReorderDragOver(section.id)"
                            @drop.prevent="onSectionDrop(section.id)"
                            @dragend="onSectionDragEnd"
                        >
                            <div class="flex items-center gap-2">
                                <MaterialDesignIcon
                                    :icon-name="section.collapsed ? 'chevron-right' : 'chevron-down'"
                                    class="size-4 text-gray-400"
                                />
                                <span
                                    class="text-xs font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300"
                                >
                                    {{ section.name }}
                                </span>
                                <span
                                    v-if="section.collapsed"
                                    class="text-[10px] font-semibold text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-zinc-800 px-2 py-0.5 rounded-full"
                                >
                                    {{ section.favourites.length }}
                                </span>
                            </div>
                            <div class="flex items-center gap-1" @click.stop>
                                <button
                                    type="button"
                                    class="p-1 text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 rounded-lg transition"
                                    @click="openSectionContextMenu($event, section)"
                                >
                                    <MaterialDesignIcon icon-name="dots-vertical" class="size-4" />
                                </button>
                            </div>
                        </div>
                        <div class="h-px bg-gray-200 dark:bg-zinc-800 mx-1"></div>
                        <div v-if="!section.collapsed" class="space-y-2 pt-2 pb-1 px-1">
                            <div
                                v-for="favourite of section.favourites"
                                :key="favourite.destination_hash"
                                class="favourite-card relative"
                                :class="[
                                    favourite.destination_hash === selectedDestinationHash
                                        ? 'favourite-card--active'
                                        : '',
                                    draggingFavouriteHash === favourite.destination_hash
                                        ? 'favourite-card--dragging'
                                        : '',
                                ]"
                                draggable="true"
                                @click="onFavouriteClick(favourite)"
                                @contextmenu.prevent="openFavouriteContextMenu($event, favourite, section.id)"
                                @dragstart="onFavouriteDragStart($event, favourite, section.id)"
                                @dragover.prevent="onFavouriteDragOver($event)"
                                @drop.prevent="onFavouriteDrop($event, section.id, favourite)"
                                @dragend="onFavouriteDragEnd"
                            >
                                <div
                                    v-if="
                                        GlobalState.config.banished_effect_enabled &&
                                        isBlocked(favourite.destination_hash)
                                    "
                                    class="banished-overlay"
                                    :style="{ background: GlobalState.config.banished_color + '33' }"
                                >
                                    <span
                                        class="banished-text !text-[10px] !opacity-100 !tracking-widest !border !px-1 !py-0.5 !text-white !shadow-lg"
                                        :style="{ 'background-color': GlobalState.config.banished_color }"
                                        >{{ GlobalState.config.banished_text }}</span
                                    >
                                </div>

                                <div class="favourite-card__icon flex-shrink-0">
                                    <MaterialDesignIcon icon-name="server-network" class="w-5 h-5" />
                                </div>
                                <div class="min-w-0 flex-1">
                                    <div
                                        class="text-sm font-semibold text-gray-900 dark:text-white truncate"
                                        :title="favourite.display_name"
                                    >
                                        {{ favourite.display_name }}
                                    </div>
                                    <div
                                        class="text-xs text-gray-500 dark:text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 cursor-pointer inline-flex items-center"
                                        :title="$t('common.copy_to_clipboard')"
                                        @click.stop="copyToClipboard(favourite.destination_hash, 'Address')"
                                    >
                                        {{ formatDestinationHash(favourite.destination_hash) }}
                                    </div>
                                </div>
                                <IconButton
                                    class="flex-shrink-0 text-gray-500 dark:text-gray-300"
                                    @click.stop="openFavouriteContextMenu($event, favourite, section.id)"
                                >
                                    <MaterialDesignIcon icon-name="dots-vertical" class="w-5 h-5" />
                                </IconButton>
                            </div>
                            <div
                                v-if="section.favourites.length === 0"
                                class="text-xs text-gray-500 dark:text-gray-400 px-3 pb-2 italic"
                            >
                                No favourites in this section.
                            </div>
                        </div>
                    </div>
                </div>
                <div v-else class="empty-state">
                    <MaterialDesignIcon icon-name="star-outline" class="w-8 h-8" />
                    <div class="font-semibold">No favourites match your search</div>
                    <div class="text-sm text-gray-500 dark:text-gray-400">Try a different search term.</div>
                </div>
            </div>

            <!-- Favourite Context Menu (Teleport to body to avoid overflow clipping) -->
            <Teleport to="body">
                <div
                    v-if="favouriteContextMenu.show"
                    v-click-outside="{
                        handler: () => {
                            if (!favouriteContextMenu.justOpened) closeContextMenus();
                        },
                        capture: true,
                    }"
                    class="fixed z-[200] min-w-[220px] bg-white dark:bg-zinc-800 rounded-2xl shadow-2xl border border-gray-200 dark:border-zinc-700 py-1.5 overflow-hidden animate-in fade-in zoom-in duration-100"
                    :style="{ top: favouriteContextMenu.y + 'px', left: favouriteContextMenu.x + 'px' }"
                >
                    <button
                        type="button"
                        class="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 dark:text-zinc-300 hover:bg-gray-100 dark:hover:bg-zinc-700 transition-all active:scale-95"
                        @click="renameFavouriteFromContext"
                    >
                        <MaterialDesignIcon icon-name="pencil" class="size-4 text-gray-400" />
                        <span class="font-medium">{{ $t("nomadnet.rename") }}</span>
                    </button>
                    <button
                        v-if="!isBlocked(favouriteContextMenu.targetHash)"
                        type="button"
                        class="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all active:scale-95"
                        @click="banishFavouriteFromContext"
                    >
                        <MaterialDesignIcon icon-name="gavel" class="size-4 text-red-400" />
                        <span class="font-medium">{{ $t("nomadnet.block_node") }}</span>
                    </button>
                    <button
                        v-else
                        type="button"
                        class="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20 transition-all active:scale-95"
                        @click="unblockFavouriteFromContext"
                    >
                        <MaterialDesignIcon icon-name="check-circle" class="size-4 text-green-400" />
                        <span class="font-medium">{{ $t("nomadnet.lift_banishment") }}</span>
                    </button>
                    <button
                        type="button"
                        class="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all active:scale-95"
                        @click="removeFavouriteFromContext"
                    >
                        <MaterialDesignIcon icon-name="trash-can" class="size-4 text-red-400" />
                        <span class="font-medium">{{ $t("nomadnet.remove") }}</span>
                    </button>
                <div class="border-t border-gray-100 dark:border-zinc-700 my-1.5 mx-2"></div>
                <div
                    class="px-4 py-1.5 text-[10px] font-black text-gray-400 dark:text-zinc-500 uppercase tracking-widest"
                >
                    Move to Section
                </div>
                <div class="max-h-56 overflow-y-auto custom-scrollbar">
                    <button
                        v-for="section in sectionsWithFavourites"
                        :key="section.id + '-move'"
                        type="button"
                        class="w-full flex items-center gap-3 px-4 py-2 text-sm text-gray-700 dark:text-zinc-300 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:text-blue-600 dark:hover:text-blue-400 transition-all active:scale-95"
                        @click="moveContextFavouriteToSection(section.id)"
                    >
                        <MaterialDesignIcon icon-name="folder" class="size-4 opacity-70" />
                        <span class="truncate">{{ section.name }}</span>
                    </button>
                </div>
                </div>
            </Teleport>

            <!-- Section Context Menu (Teleport to body) -->
            <Teleport to="body">
                <div
                    v-if="sectionContextMenu.show"
                    v-click-outside="{ handler: closeContextMenus, capture: true }"
                    class="fixed z-[200] min-w-[200px] bg-white dark:bg-zinc-800 rounded-2xl shadow-2xl border border-gray-200 dark:border-zinc-700 py-1.5 overflow-hidden animate-in fade-in zoom-in duration-100"
                    :style="{ top: sectionContextMenu.y + 'px', left: sectionContextMenu.x + 'px' }"
                >
                <button
                    type="button"
                    class="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 dark:text-zinc-300 hover:bg-gray-100 dark:hover:bg-zinc-700 transition-all active:scale-95"
                    @click="renameSectionFromContext"
                >
                    <MaterialDesignIcon icon-name="pencil" class="size-4 text-gray-400" />
                    <span class="font-medium">Rename Section</span>
                </button>
                <button
                    type="button"
                    class="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all active:scale-95"
                    :disabled="sectionContextMenu.sectionId === defaultSectionId"
                    :class="sectionContextMenu.sectionId === defaultSectionId ? 'opacity-50 cursor-not-allowed' : ''"
                    @click="removeSectionFromContext"
                >
                    <MaterialDesignIcon icon-name="delete" class="size-4 text-red-400" />
                    <span class="font-medium">Delete Section</span>
                </button>
                </div>
            </Teleport>
        </div>

        <div v-else class="flex-1 flex flex-col min-h-0">
            <div class="p-3 border-b border-gray-200 dark:border-zinc-800">
                <input
                    :value="nodesSearchTerm"
                    type="text"
                    :placeholder="$t('nomadnet.search_placeholder_announces', { count: totalNodesCount })"
                    class="input-field w-full rounded-none"
                    @input="onNodesSearchInput"
                />
            </div>
            <div class="flex-1 overflow-y-auto px-2 pb-4" @scroll="onNodesScroll">
                <div v-if="searchedNodes.length > 0" class="space-y-2 pt-2">
                    <div
                        v-for="node of searchedNodes"
                        :key="node.destination_hash"
                        class="announce-card relative"
                        :class="{ 'announce-card--active': node.destination_hash === selectedDestinationHash }"
                        @contextmenu.prevent="openAnnounceContextMenu($event, node)"
                    >
                        <!-- banished overlay -->
                        <div
                            v-if="GlobalState.config.banished_effect_enabled && isBlocked(node.identity_hash)"
                            class="banished-overlay"
                            :style="{ background: GlobalState.config.banished_color + '33' }"
                        >
                            <span
                                class="banished-text !text-[10px] !opacity-100 !tracking-widest !border !px-1 !py-0.5 !text-white !shadow-lg"
                                :style="{ 'background-color': GlobalState.config.banished_color }"
                                >{{ GlobalState.config.banished_text }}</span
                            >
                        </div>

                        <div class="flex items-center gap-3 flex-1 min-w-0 cursor-pointer" @click="onNodeClick(node)">
                            <div class="announce-card__icon flex-shrink-0">
                                <MaterialDesignIcon icon-name="satellite-uplink" class="w-5 h-5" />
                            </div>
                            <div class="min-w-0 flex-1">
                                <div
                                    class="text-sm font-semibold text-gray-900 dark:text-white truncate"
                                    :title="node.display_name"
                                >
                                    {{ node.display_name }}
                                </div>
                                <div class="text-xs text-gray-500 dark:text-gray-400 flex flex-col gap-0.5">
                                    <span class="truncate">{{
                                        $t("nomadnet.announced_time_ago", { time: formatTimeAgo(node.updated_at) })
                                    }}</span>
                                    <span
                                        class="cursor-pointer hover:text-blue-500 dark:hover:text-blue-400 inline-flex items-center"
                                        :title="$t('common.copy_to_clipboard')"
                                        @click.stop="copyToClipboard(node.destination_hash, 'Address')"
                                    >
                                        {{ formatDestinationHash(node.destination_hash) }}
                                    </span>
                                </div>
                            </div>
                        </div>
                        <div class="flex-shrink-0">
                            <DropDownMenu>
                            <template #button>
                                <IconButton>
                                    <MaterialDesignIcon icon-name="dots-vertical" class="w-5 h-5" />
                                </IconButton>
                            </template>
                            <template #items>
                                <DropDownMenuItem v-if="!isBlocked(node.identity_hash)" @click.stop="onBlockNode(node)">
                                    <MaterialDesignIcon icon-name="gavel" class="w-5 h-5 text-red-500" />
                                    <span class="text-red-500">{{ $t("nomadnet.block_node") }}</span>
                                </DropDownMenuItem>
                                <DropDownMenuItem v-else @click.stop="onUnblockNode(node.identity_hash)">
                                    <MaterialDesignIcon icon-name="check-circle" class="w-5 h-5 text-green-500" />
                                    <span class="text-green-500">{{ $t("nomadnet.lift_banishment") }}</span>
                                </DropDownMenuItem>
                            </template>
                        </DropDownMenu>
                        </div>
                    </div>

                    <!-- loading more spinner -->
                    <div v-if="isLoadingMoreNodes" class="p-4 text-center">
                        <MaterialDesignIcon icon-name="loading" class="size-6 animate-spin text-gray-400" />
                    </div>
                </div>
                <div v-else class="empty-state">
                    <MaterialDesignIcon icon-name="radar" class="w-8 h-8" />
                    <div class="font-semibold">{{ $t("nomadnet.no_announces_yet") }}</div>
                    <div class="text-sm text-gray-500 dark:text-gray-400">{{ $t("nomadnet.listening_for_peers") }}</div>
                </div>
            </div>

            <!-- Announce Context Menu (right-click, Teleport to body) -->
            <Teleport to="body">
                <div
                    v-if="announceContextMenu.show"
                    v-click-outside="{
                        handler: () => {
                            if (!announceContextMenu.justOpened) closeContextMenus();
                        },
                        capture: true,
                    }"
                    class="fixed z-[200] min-w-[200px] bg-white dark:bg-zinc-800 rounded-2xl shadow-2xl border border-gray-200 dark:border-zinc-700 py-1.5 overflow-hidden animate-in fade-in zoom-in duration-100"
                    :style="{ top: announceContextMenu.y + 'px', left: announceContextMenu.x + 'px' }"
                >
                    <button
                        v-if="!isFavourite(announceContextMenu.node?.destination_hash)"
                        type="button"
                        class="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 dark:text-zinc-300 hover:bg-gray-100 dark:hover:bg-zinc-700 transition-all active:scale-95"
                        @click="addFavouriteFromContext"
                    >
                        <MaterialDesignIcon icon-name="star-outline" class="size-4 text-yellow-500" />
                        <span class="font-medium">{{ $t("nomadnet.add_favourite") }}</span>
                    </button>
                    <button
                        v-if="!isBlocked(announceContextMenu.node?.identity_hash)"
                        type="button"
                        class="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all active:scale-95"
                        @click="blockAnnounceFromContext"
                    >
                        <MaterialDesignIcon icon-name="gavel" class="size-4 text-red-400" />
                        <span class="font-medium">{{ $t("nomadnet.block_node") }}</span>
                    </button>
                    <button
                        v-else
                        type="button"
                        class="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20 transition-all active:scale-95"
                        @click="unblockAnnounceFromContext"
                    >
                        <MaterialDesignIcon icon-name="check-circle" class="size-4 text-green-400" />
                        <span class="font-medium">{{ $t("nomadnet.lift_banishment") }}</span>
                    </button>
                </div>
            </Teleport>
        </div>
    </div>
</template>

<script>
import Utils from "../../js/Utils";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import DropDownMenu from "../DropDownMenu.vue";
import IconButton from "../IconButton.vue";
import DropDownMenuItem from "../DropDownMenuItem.vue";
import DialogUtils from "../../js/DialogUtils";
import GlobalState from "../../js/GlobalState";
import GlobalEmitter from "../../js/GlobalEmitter";
import ToastUtils from "../../js/ToastUtils";

export default {
    name: "NomadNetworkSidebar",
    components: { DropDownMenuItem, IconButton, DropDownMenu, MaterialDesignIcon },
    props: {
        nodes: {
            type: Object,
            required: true,
        },
        favourites: {
            type: Array,
            required: true,
        },
        selectedDestinationHash: {
            type: String,
            required: true,
        },
        nodesSearchTerm: {
            type: String,
            default: "",
        },
        totalNodesCount: {
            type: Number,
            default: 0,
        },
        isLoadingMoreNodes: {
            type: Boolean,
            default: false,
        },
        hasMoreNodes: {
            type: Boolean,
            default: false,
        },
    },
    emits: [
        "node-click",
        "rename-favourite",
        "remove-favourite",
        "add-favourite",
        "nodes-search-changed",
        "load-more-nodes",
    ],
    data() {
        return {
            GlobalState,
            tab: "favourites",
            favouritesSearchTerm: "",
            defaultSectionId: "default",
            sections: [],
            sectionOrder: [],
            favouritesBySection: {},
            draggingFavouriteHash: null,
            draggingFavouriteSectionId: null,
            dragOverSectionId: null,
            draggingSectionId: null,
            draggingSectionOverId: null,
            favouriteContextMenu: {
                show: false,
                x: 0,
                y: 0,
                targetHash: null,
                targetSectionId: null,
                justOpened: false,
            },
            sectionContextMenu: {
                show: false,
                x: 0,
                y: 0,
                sectionId: null,
            },
            announceContextMenu: {
                show: false,
                x: 0,
                y: 0,
                node: null,
                justOpened: false,
            },
        };
    },
    computed: {
        blockedDestinations() {
            return GlobalState.blockedDestinations;
        },
        nodesCount() {
            return Object.keys(this.nodes).length;
        },
        nodesOrderedByLatestAnnounce() {
            const nodes = Object.values(this.nodes);
            return nodes.sort(function (nodeA, nodeB) {
                // order by updated_at desc
                const nodeAUpdatedAt = new Date(nodeA.updated_at).getTime();
                const nodeBUpdatedAt = new Date(nodeB.updated_at).getTime();
                return nodeBUpdatedAt - nodeAUpdatedAt;
            });
        },
        searchedNodes() {
            return this.nodesOrderedByLatestAnnounce.filter((node) => {
                const search = this.nodesSearchTerm.toLowerCase();
                const matchesDisplayName = node.display_name.toLowerCase().includes(search);
                const matchesDestinationHash = node.destination_hash.toLowerCase().includes(search);
                return matchesDisplayName || matchesDestinationHash;
            });
        },
        orderedSections() {
            const map = {};
            this.sections.forEach((section) => {
                map[section.id] = section;
            });
            const ids = this.sectionOrder.length > 0 ? this.sectionOrder : this.sections.map((section) => section.id);
            return ids.map((id) => map[id]).filter((section) => section);
        },
        sectionsWithFavourites() {
            const search = this.favouritesSearchTerm.toLowerCase();
            return this.orderedSections.map((section) => {
                const hashes = this.favouritesBySection[section.id] || [];
                const favourites = hashes
                    .map((hash) => this.favourites.find((fav) => fav.destination_hash === hash))
                    .filter((fav) => fav)
                    .filter((fav) => this.matchesFavouriteSearch(fav, search));
                return { ...section, favourites };
            });
        },
        hasFavouriteResults() {
            if (this.favourites.length === 0) {
                return false;
            }
            if (this.favouritesSearchTerm.trim() === "") {
                return true;
            }
            return this.sectionsWithFavourites.some((section) => section.favourites.length > 0);
        },
    },
    watch: {
        favourites: {
            handler() {
                this.ensureFavouriteLayout();
            },
            deep: true,
        },
    },
    mounted() {
        this.loadFavouriteLayout();
        this.ensureFavouriteLayout();
    },
    methods: {
        matchesFavouriteSearch(favourite, searchTerm = this.favouritesSearchTerm.toLowerCase()) {
            const matchesDisplayName = favourite.display_name.toLowerCase().includes(searchTerm);
            const matchesCustomDisplayName =
                favourite.custom_display_name?.toLowerCase()?.includes(searchTerm) === true;
            const matchesDestinationHash = favourite.destination_hash.toLowerCase().includes(searchTerm);
            return matchesDisplayName || matchesCustomDisplayName || matchesDestinationHash;
        },
        buildDefaultSection() {
            return {
                id: this.defaultSectionId,
                name: this.$t("nomadnet.favourites"),
                collapsed: false,
            };
        },
        resetDefaultSections() {
            const defaultSection = this.buildDefaultSection();
            this.sections = [defaultSection];
            this.sectionOrder = [defaultSection.id];
            this.favouritesBySection = { [defaultSection.id]: [] };
        },
        loadFavouriteLayout() {
            try {
                const stored = localStorage.getItem("meshchat.nomadnet.favourites.layout");
                if (stored) {
                    const parsed = JSON.parse(stored);
                    this.sections = parsed.sections || [];
                    this.sectionOrder =
                        parsed.sectionOrder ||
                        (parsed.sections ? parsed.sections.map((section) => section.id) : this.sectionOrder);
                    this.favouritesBySection = parsed.favouritesBySection || {};
                    return;
                }
                const legacyOrder = localStorage.getItem("meshchat.nomadnet.favourites");
                if (legacyOrder) {
                    const parsedOrder = JSON.parse(legacyOrder);
                    const defaultSection = this.buildDefaultSection();
                    this.sections = [defaultSection];
                    this.sectionOrder = [defaultSection.id];
                    this.favouritesBySection = { [defaultSection.id]: parsedOrder };
                }
            } catch (e) {
                console.log(e);
            }
            if (this.sections.length === 0) {
                this.resetDefaultSections();
            }
        },
        persistFavouriteLayout() {
            try {
                localStorage.setItem(
                    "meshchat.nomadnet.favourites.layout",
                    JSON.stringify({
                        sections: this.sections,
                        sectionOrder: this.sectionOrder,
                        favouritesBySection: this.favouritesBySection,
                    })
                );
            } catch (e) {
                console.log(e);
            }
        },
        ensureFavouriteLayout() {
            if (this.sections.length === 0) {
                this.resetDefaultSections();
            }
            const hashes = this.favourites.map((fav) => fav.destination_hash);
            const sectionIds = new Set();
            const sanitizedSections = [];
            this.sections.forEach((section) => {
                if (!section || !section.id || sectionIds.has(section.id)) {
                    return;
                }
                sectionIds.add(section.id);
                sanitizedSections.push({
                    id: section.id,
                    name: section.name || this.$t("nomadnet.favourites"),
                    collapsed: section.collapsed === true ? true : false,
                });
            });
            if (!sectionIds.has(this.defaultSectionId)) {
                const defaultSection = this.buildDefaultSection();
                sanitizedSections.unshift(defaultSection);
                sectionIds.add(defaultSection.id);
            }
            this.sections = sanitizedSections;
            const existingOrder = Array.isArray(this.sectionOrder) ? this.sectionOrder : [];
            const filteredOrder = existingOrder.filter((id) => sectionIds.has(id));
            const remaining = sanitizedSections
                .map((section) => section.id)
                .filter((id) => !filteredOrder.includes(id));
            this.sectionOrder = [...filteredOrder, ...remaining];

            const nextFavouritesBySection = {};
            sanitizedSections.forEach((section) => {
                const existing = this.favouritesBySection[section.id] || [];
                nextFavouritesBySection[section.id] = existing.filter((hash) => hashes.includes(hash));
            });
            const assigned = new Set(Object.values(nextFavouritesBySection).flat());
            hashes.forEach((hash) => {
                if (!assigned.has(hash)) {
                    nextFavouritesBySection[this.defaultSectionId].push(hash);
                    assigned.add(hash);
                }
            });
            this.favouritesBySection = nextFavouritesBySection;
            this.persistFavouriteLayout();
        },
        isBlocked(identityHash) {
            return this.blockedDestinations.some((b) => b.destination_hash === identityHash);
        },
        isFavourite(destinationHash) {
            return this.favourites.some((f) => f.destination_hash === destinationHash);
        },
        addFavouriteFromContext() {
            const node = this.announceContextMenu.node;
            if (!node) {
                this.closeContextMenus();
                return;
            }
            this.closeContextMenus();
            this.$emit("add-favourite", node);
        },
        async blockAnnounceFromContext() {
            const node = this.announceContextMenu.node;
            if (!node) {
                this.closeContextMenus();
                return;
            }
            this.closeContextMenus();
            await this.onBlockNode(node);
        },
        async unblockAnnounceFromContext() {
            const node = this.announceContextMenu.node;
            if (!node) {
                this.closeContextMenus();
                return;
            }
            this.closeContextMenus();
            await this.onUnblockNode(node.identity_hash);
        },
        async onBlockNode(node) {
            if (!(await DialogUtils.confirm(this.$t("nomadnet.block_node_confirm", { name: node.display_name })))) {
                return;
            }

            try {
                await window.axios.post("/api/v1/blocked-destinations", {
                    destination_hash: node.identity_hash,
                });
                GlobalEmitter.emit("block-status-changed");
                DialogUtils.alert(this.$t("nomadnet.node_blocked_successfully"));
            } catch (e) {
                DialogUtils.alert(this.$t("nomadnet.failed_to_block_node"));
                console.log(e);
            }
        },
        async onUnblockNode(identityHash) {
            try {
                await window.axios.delete(`/api/v1/blocked-destinations/${identityHash}`);
                GlobalEmitter.emit("block-status-changed");
                DialogUtils.alert(this.$t("nomadnet.banishment_lifted"));
            } catch (e) {
                DialogUtils.alert(this.$t("nomadnet.failed_lift_banishment"));
                console.log(e);
            }
        },
        onNodeClick(node) {
            if (this.isBlocked(node.identity_hash || node.destination_hash)) {
                return;
            }
            this.$emit("node-click", node);
        },
        onFavouriteClick(favourite) {
            if (this.isBlocked(favourite.destination_hash)) {
                return;
            }
            this.onNodeClick(favourite);
        },
        onRenameFavourite(favourite) {
            this.$emit("rename-favourite", favourite);
        },
        onRemoveFavourite(favourite) {
            this.$emit("remove-favourite", favourite);
        },
        onFavouriteDragStart(event, favourite, sectionId) {
            try {
                if (event?.dataTransfer) {
                    event.dataTransfer.effectAllowed = "move";
                    event.dataTransfer.setData("text/plain", favourite.destination_hash);
                }
            } catch {
                // ignore for browsers that prevent setting drag meta
            }
            this.draggingFavouriteHash = favourite.destination_hash;
            this.draggingFavouriteSectionId = sectionId;
        },
        onFavouriteDragOver(event) {
            if (event?.dataTransfer) {
                event.dataTransfer.dropEffect = "move";
            }
        },
        onFavouriteDrop(event, targetSectionId, targetFavourite) {
            if (!this.draggingFavouriteHash || this.draggingFavouriteHash === targetFavourite.destination_hash) {
                return;
            }
            this.moveFavouriteToSection(this.draggingFavouriteHash, targetSectionId, targetFavourite.destination_hash);
        },
        onFavouriteDragEnd() {
            this.draggingFavouriteHash = null;
            this.draggingFavouriteSectionId = null;
            this.dragOverSectionId = null;
        },
        onSectionDragOver(sectionId) {
            this.dragOverSectionId = sectionId;
        },
        onSectionDragLeave() {
            this.dragOverSectionId = null;
        },
        onDropOnSection(sectionId) {
            if (!this.draggingFavouriteHash) {
                return;
            }
            this.moveFavouriteToSection(this.draggingFavouriteHash, sectionId);
        },
        onSectionDragStart(sectionId) {
            this.draggingSectionId = sectionId;
        },
        onSectionReorderDragOver(sectionId) {
            if (!this.draggingSectionId || this.draggingSectionId === sectionId) {
                return;
            }
            this.draggingSectionOverId = sectionId;
        },
        onSectionDrop(targetSectionId) {
            if (!this.draggingSectionId || this.draggingSectionId === targetSectionId) {
                this.onSectionDragEnd();
                return;
            }
            const currentOrder = [...this.sectionOrder];
            const fromIndex = currentOrder.indexOf(this.draggingSectionId);
            const toIndex = currentOrder.indexOf(targetSectionId);
            if (fromIndex === -1 || toIndex === -1) {
                this.onSectionDragEnd();
                return;
            }
            currentOrder.splice(fromIndex, 1);
            currentOrder.splice(toIndex, 0, this.draggingSectionId);
            this.sectionOrder = currentOrder;
            this.persistFavouriteLayout();
            this.onSectionDragEnd();
        },
        onSectionDragEnd() {
            this.draggingSectionId = null;
            this.draggingSectionOverId = null;
        },
        moveFavouriteToSection(hash, targetSectionId, beforeHash = null) {
            if (!hash || !targetSectionId) {
                return;
            }
            const updated = {};
            Object.keys(this.favouritesBySection).forEach((sectionKey) => {
                updated[sectionKey] = (this.favouritesBySection[sectionKey] || []).filter((value) => value !== hash);
            });

            if (!updated[targetSectionId]) {
                updated[targetSectionId] = [];
            }
            const targetList = [...updated[targetSectionId]];
            if (beforeHash) {
                const insertIndex = targetList.indexOf(beforeHash);
                if (insertIndex === -1) {
                    targetList.push(hash);
                } else {
                    targetList.splice(insertIndex, 0, hash);
                }
            } else {
                targetList.push(hash);
            }
            updated[targetSectionId] = targetList;
            this.favouritesBySection = updated;
            this.persistFavouriteLayout();
            this.draggingFavouriteHash = null;
            this.draggingFavouriteSectionId = null;
            this.dragOverSectionId = null;
        },
        openFavouriteContextMenu(event, favourite, sectionId) {
            this.favouriteContextMenu = {
                show: true,
                justOpened: true,
                x: event.clientX,
                y: event.clientY,
                targetHash: favourite.destination_hash,
                targetSectionId: sectionId,
            };
            this.sectionContextMenu.show = false;
            setTimeout(() => {
                this.favouriteContextMenu.justOpened = false;
            }, 50);
        },
        openSectionContextMenu(event, section) {
            this.sectionContextMenu = {
                show: true,
                x: event.pageX || event.clientX,
                y: event.pageY || event.clientY,
                sectionId: section.id,
            };
            this.favouriteContextMenu.show = false;
        },
        closeContextMenus() {
            this.favouriteContextMenu.show = false;
            this.sectionContextMenu.show = false;
            this.announceContextMenu.show = false;
        },
        openAnnounceContextMenu(event, node) {
            this.announceContextMenu = {
                show: true,
                justOpened: true,
                x: event.clientX,
                y: event.clientY,
                node,
            };
            this.favouriteContextMenu.show = false;
            this.sectionContextMenu.show = false;
            setTimeout(() => {
                this.announceContextMenu.justOpened = false;
            }, 50);
        },
        getFavouriteByHash(hash) {
            return this.favourites.find((fav) => fav.destination_hash === hash);
        },
        renameFavouriteFromContext() {
            const favourite = this.getFavouriteByHash(this.favouriteContextMenu.targetHash);
            if (!favourite) {
                this.closeContextMenus();
                return;
            }
            this.closeContextMenus();
            this.onRenameFavourite(favourite);
        },
        removeFavouriteFromContext() {
            const favourite = this.getFavouriteByHash(this.favouriteContextMenu.targetHash);
            if (!favourite) {
                this.closeContextMenus();
                return;
            }
            this.closeContextMenus();
            this.onRemoveFavourite(favourite);
        },
        async banishFavouriteFromContext() {
            const favourite = this.getFavouriteByHash(this.favouriteContextMenu.targetHash);
            if (!favourite) {
                this.closeContextMenus();
                return;
            }
            this.closeContextMenus();
            if (
                !(await DialogUtils.confirm(
                    this.$t("nomadnet.block_node_confirm", { name: favourite.display_name || favourite.custom_display_name })
                ))
            ) {
                return;
            }
            try {
                await window.axios.post("/api/v1/blocked-destinations", {
                    destination_hash: favourite.destination_hash,
                });
                GlobalEmitter.emit("block-status-changed");
                DialogUtils.alert(this.$t("nomadnet.node_blocked_successfully"));
            } catch (e) {
                DialogUtils.alert(this.$t("nomadnet.failed_to_block_node"));
                console.error(e);
            }
        },
        async unblockFavouriteFromContext() {
            const hash = this.favouriteContextMenu.targetHash;
            if (!hash) {
                this.closeContextMenus();
                return;
            }
            this.closeContextMenus();
            try {
                await window.axios.delete(`/api/v1/blocked-destinations/${hash}`);
                GlobalEmitter.emit("block-status-changed");
                DialogUtils.alert(this.$t("nomadnet.banishment_lifted"));
            } catch (e) {
                DialogUtils.alert(this.$t("nomadnet.failed_lift_banishment"));
                console.error(e);
            }
        },
        moveContextFavouriteToSection(sectionId) {
            if (!this.favouriteContextMenu.targetHash) {
                return;
            }
            this.moveFavouriteToSection(this.favouriteContextMenu.targetHash, sectionId);
            this.closeContextMenus();
        },
        toggleSectionCollapse(sectionId) {
            const idx = this.sections.findIndex((section) => section.id === sectionId);
            if (idx === -1) {
                return;
            }
            const updated = [...this.sections];
            const section = { ...updated[idx] };
            section.collapsed = !section.collapsed;
            updated[idx] = section;
            this.sections = updated;
            this.persistFavouriteLayout();
        },
        async createSection() {
            const name = await DialogUtils.prompt(
                this.$t("nomadnet.enter_section_name"),
                this.$t("nomadnet.new_section")
            );
            if (!name) {
                return;
            }
            const section = {
                id: `section-${Date.now()}`,
                name,
                collapsed: false,
            };
            this.sections = [...this.sections, section];
            this.sectionOrder = [...this.sectionOrder, section.id];
            this.favouritesBySection = { ...this.favouritesBySection, [section.id]: [] };
            this.persistFavouriteLayout();
        },
        async renameSectionFromContext() {
            const section = this.sections.find((sec) => sec.id === this.sectionContextMenu.sectionId);
            if (!section) {
                this.closeContextMenus();
                return;
            }
            const name = await DialogUtils.prompt(this.$t("nomadnet.rename_section"), section.name);
            if (!name || name === section.name) {
                this.closeContextMenus();
                return;
            }
            this.sections = this.sections.map((sec) => (sec.id === section.id ? { ...sec, name } : sec));
            this.persistFavouriteLayout();
            this.closeContextMenus();
        },
        async removeSectionFromContext() {
            const sectionId = this.sectionContextMenu.sectionId;
            if (!sectionId || sectionId === this.defaultSectionId) {
                this.closeContextMenus();
                return;
            }
            const confirmed = await DialogUtils.confirm(this.$t("nomadnet.delete_section_confirm"));
            if (!confirmed) {
                this.closeContextMenus();
                return;
            }
            const retainedSections = this.sections.filter((section) => section.id !== sectionId);
            const migrated = this.favouritesBySection[sectionId] || [];
            const nextMap = { ...this.favouritesBySection };
            delete nextMap[sectionId];
            nextMap[this.defaultSectionId] = [...(nextMap[this.defaultSectionId] || []), ...migrated];
            this.sections = retainedSections;
            this.sectionOrder = this.sectionOrder.filter((id) => id !== sectionId);
            this.favouritesBySection = nextMap;
            this.persistFavouriteLayout();
            this.closeContextMenus();
        },
        formatTimeAgo: function (datetimeString) {
            return Utils.formatTimeAgo(datetimeString);
        },
        formatDestinationHash: function (destinationHash) {
            return Utils.formatDestinationHash(destinationHash);
        },
        copyToClipboard(text, label) {
            if (!text) return;
            navigator.clipboard.writeText(text);
            ToastUtils.success(`${label} copied to clipboard`);
        },
        onNodesSearchInput(event) {
            this.$emit("nodes-search-changed", event.target.value);
        },
        onNodesScroll(event) {
            const element = event.target;
            // if scrolled near bottom (within 200px)
            if (element.scrollHeight - element.scrollTop - element.clientHeight < 200) {
                if (this.hasMoreNodes && !this.isLoadingMoreNodes) {
                    this.$emit("load-more-nodes");
                }
            }
        },
    },
};
</script>

<style scoped>
.sidebar-tab {
    @apply w-1/2 py-3 text-sm font-semibold text-gray-500 dark:text-gray-400 border-b-2 border-transparent transition;
}
.sidebar-tab--active {
    @apply text-blue-600 border-blue-500 dark:text-blue-300 dark:border-blue-400;
}
.favourite-card {
    @apply flex items-center gap-3 rounded-2xl border border-gray-200 dark:border-zinc-800 bg-white/90 dark:bg-zinc-900/70 px-3 py-2 cursor-pointer hover:border-blue-400 dark:hover:border-blue-500 hover:z-10;
}
.favourite-card--active {
    @apply border-blue-500 dark:border-blue-400 bg-blue-50/60 dark:bg-blue-900/30;
}
.favourite-card__icon,
.announce-card__icon {
    @apply w-10 h-10 rounded-xl bg-gray-100 dark:bg-zinc-800 flex items-center justify-center text-gray-500 dark:text-gray-300;
}
.favourite-card--dragging {
    @apply opacity-60 ring-2 ring-blue-300 dark:ring-blue-600;
}
.announce-card {
    @apply flex items-center gap-3 rounded-2xl border border-gray-200 dark:border-zinc-800 bg-white/90 dark:bg-zinc-900/70 px-3 py-2 hover:border-blue-400 dark:hover:border-blue-500 hover:z-10;
}
.announce-card--active {
    @apply border-blue-500 dark:border-blue-400 bg-blue-50/70 dark:bg-blue-900/30;
}
.empty-state {
    @apply flex flex-col items-center justify-center text-center gap-2 text-gray-500 dark:text-gray-400 mt-20;
}
</style>
