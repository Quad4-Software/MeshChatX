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
                    class="input-field"
                />
            </div>
            <div class="flex-1 overflow-y-auto px-2 pb-4">
                <div v-if="searchedFavourites.length > 0" class="space-y-2 pt-2">
                    <div
                        v-for="favourite of searchedFavourites"
                        :key="favourite.destination_hash"
                        class="favourite-card relative"
                        :class="[
                            favourite.destination_hash === selectedDestinationHash ? 'favourite-card--active' : '',
                            draggingFavouriteHash === favourite.destination_hash ? 'favourite-card--dragging' : '',
                        ]"
                        draggable="true"
                        @click="onFavouriteClick(favourite)"
                        @dragstart="onFavouriteDragStart($event, favourite)"
                        @dragover.prevent="onFavouriteDragOver($event)"
                        @drop.prevent="onFavouriteDrop($event, favourite)"
                        @dragend="onFavouriteDragEnd"
                    >
                        <!-- banished overlay -->
                        <div
                            v-if="GlobalState.config.banished_effect_enabled && isBlocked(favourite.destination_hash)"
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
                            <div class="text-xs text-gray-500 dark:text-gray-400">
                                {{ formatDestinationHash(favourite.destination_hash) }}
                            </div>
                        </div>
                        <DropDownMenu>
                            <template #button>
                                <IconButton>
                                    <MaterialDesignIcon icon-name="dots-vertical" class="w-5 h-5" />
                                </IconButton>
                            </template>
                            <template #items>
                                <DropDownMenuItem @click="onRenameFavourite(favourite)">
                                    <MaterialDesignIcon icon-name="pencil" class="w-5 h-5" />
                                    <span>{{ $t("nomadnet.rename") }}</span>
                                </DropDownMenuItem>
                                <DropDownMenuItem @click="onRemoveFavourite(favourite)">
                                    <MaterialDesignIcon icon-name="trash-can" class="w-5 h-5 text-red-500" />
                                    <span class="text-red-500">{{ $t("nomadnet.remove") }}</span>
                                </DropDownMenuItem>
                                <div v-if="isBlocked(favourite.destination_hash)" class="border-t">
                                    <DropDownMenuItem @click.stop="onUnblockNode(favourite.destination_hash)">
                                        <MaterialDesignIcon icon-name="check-circle" class="w-5 h-5 text-green-500" />
                                        <span class="text-green-500">Unblock Node</span>
                                    </DropDownMenuItem>
                                </div>
                            </template>
                        </DropDownMenu>
                    </div>
                </div>
                <div v-else class="empty-state">
                    <MaterialDesignIcon icon-name="star-outline" class="w-8 h-8" />
                    <div class="font-semibold">{{ $t("nomadnet.no_favourites") }}</div>
                    <div class="text-sm text-gray-500 dark:text-gray-400">
                        {{ $t("nomadnet.add_nodes_from_announces") }}
                    </div>
                </div>
            </div>
        </div>

        <div v-else class="flex-1 flex flex-col min-h-0">
            <div class="p-3 border-b border-gray-200 dark:border-zinc-800">
                <input
                    :value="nodesSearchTerm"
                    type="text"
                    :placeholder="$t('nomadnet.search_placeholder_announces', { count: totalNodesCount })"
                    class="input-field"
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
                                <div class="text-xs text-gray-500 dark:text-gray-400">
                                    {{ $t("nomadnet.announced_time_ago", { time: formatTimeAgo(node.updated_at) }) }}
                                </div>
                            </div>
                        </div>
                        <DropDownMenu>
                            <template #button>
                                <IconButton>
                                    <MaterialDesignIcon icon-name="dots-vertical" class="w-5 h-5" />
                                </IconButton>
                            </template>
                            <template #items>
                                <DropDownMenuItem v-if="!isBlocked(node.identity_hash)" @click.stop="onBlockNode(node)">
                                    <MaterialDesignIcon icon-name="block-helper" class="w-5 h-5 text-red-500" />
                                    <span class="text-red-500">{{ $t("nomadnet.block_node") }}</span>
                                </DropDownMenuItem>
                                <DropDownMenuItem v-else @click.stop="onUnblockNode(node.identity_hash)">
                                    <MaterialDesignIcon icon-name="check-circle" class="w-5 h-5 text-green-500" />
                                    <span class="text-green-500">Unblock Node</span>
                                </DropDownMenuItem>
                            </template>
                        </DropDownMenu>
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
    emits: ["node-click", "rename-favourite", "remove-favourite", "nodes-search-changed", "load-more-nodes"],
    data() {
        return {
            GlobalState,
            tab: "favourites",
            favouritesSearchTerm: "",
            favouritesOrder: [],
            draggingFavouriteHash: null,
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
        orderedFavourites() {
            return [...this.favourites].sort((a, b) => {
                return (
                    this.favouritesOrder.indexOf(a.destination_hash) - this.favouritesOrder.indexOf(b.destination_hash)
                );
            });
        },
        searchedFavourites() {
            return this.orderedFavourites.filter((favourite) => {
                const search = this.favouritesSearchTerm.toLowerCase();
                const matchesDisplayName = favourite.display_name.toLowerCase().includes(search);
                const matchesCustomDisplayName =
                    favourite.custom_display_name?.toLowerCase()?.includes(search) === true;
                const matchesDestinationHash = favourite.destination_hash.toLowerCase().includes(search);
                return matchesDisplayName || matchesCustomDisplayName || matchesDestinationHash;
            });
        },
    },
    watch: {
        favourites: {
            handler() {
                this.ensureFavouriteOrder();
            },
            deep: true,
        },
    },
    mounted() {
        this.loadFavouriteOrder();
        this.ensureFavouriteOrder();
    },
    methods: {
        isBlocked(identityHash) {
            return this.blockedDestinations.some((b) => b.destination_hash === identityHash);
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
                DialogUtils.alert("Node unblocked successfully");
            } catch (e) {
                DialogUtils.alert("Failed to unblock node");
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
        loadFavouriteOrder() {
            try {
                const stored = localStorage.getItem("meshchat.nomadnet.favourites");
                if (stored) {
                    this.favouritesOrder = JSON.parse(stored);
                }
            } catch (e) {
                console.log(e);
            }
        },
        persistFavouriteOrder() {
            localStorage.setItem("meshchat.nomadnet.favourites", JSON.stringify(this.favouritesOrder));
        },
        ensureFavouriteOrder() {
            const hashes = this.favourites.map((fav) => fav.destination_hash);
            const nextOrder = this.favouritesOrder.filter((hash) => hashes.includes(hash));
            hashes.forEach((hash) => {
                if (!nextOrder.includes(hash)) {
                    nextOrder.push(hash);
                }
            });
            if (JSON.stringify(nextOrder) !== JSON.stringify(this.favouritesOrder)) {
                this.favouritesOrder = nextOrder;
                this.persistFavouriteOrder();
            }
        },
        onFavouriteDragStart(event, favourite) {
            try {
                if (event?.dataTransfer) {
                    event.dataTransfer.effectAllowed = "move";
                    event.dataTransfer.setData("text/plain", favourite.destination_hash);
                }
            } catch {
                // ignore for browsers that prevent setting drag meta
            }
            this.draggingFavouriteHash = favourite.destination_hash;
        },
        onFavouriteDragOver(event) {
            if (event?.dataTransfer) {
                event.dataTransfer.dropEffect = "move";
            }
        },
        onFavouriteDrop(event, targetFavourite) {
            if (!this.draggingFavouriteHash || this.draggingFavouriteHash === targetFavourite.destination_hash) {
                return;
            }
            const fromIndex = this.favouritesOrder.indexOf(this.draggingFavouriteHash);
            const toIndex = this.favouritesOrder.indexOf(targetFavourite.destination_hash);
            if (fromIndex === -1 || toIndex === -1) {
                return;
            }
            const updated = [...this.favouritesOrder];
            updated.splice(fromIndex, 1);
            updated.splice(toIndex, 0, this.draggingFavouriteHash);
            this.favouritesOrder = updated;
            this.persistFavouriteOrder();
            this.draggingFavouriteHash = null;
        },
        onFavouriteDragEnd() {
            this.draggingFavouriteHash = null;
        },
        formatTimeAgo: function (datetimeString) {
            return Utils.formatTimeAgo(datetimeString);
        },
        formatDestinationHash: function (destinationHash) {
            return Utils.formatDestinationHash(destinationHash);
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
