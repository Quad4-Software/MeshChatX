<template>
    <div class="flex flex-col flex-1 h-full overflow-hidden bg-slate-50 dark:bg-zinc-950">
        <div
            class="flex items-center px-4 py-4 bg-white dark:bg-zinc-900 border-b border-gray-200 dark:border-zinc-800 shadow-sm"
        >
            <div class="flex items-center gap-3">
                <div class="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg">
                    <MaterialDesignIcon icon-name="block-helper" class="size-6 text-red-600 dark:text-red-400" />
                </div>
                <div>
                    <h1 class="text-xl font-bold text-gray-900 dark:text-white">Blocked</h1>
                    <p class="text-sm text-gray-500 dark:text-gray-400">Manage blocked users and nodes</p>
                </div>
            </div>

            <div class="ml-auto flex items-center gap-2 sm:gap-4">
                <div class="relative w-32 sm:w-64 md:w-80">
                    <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <MaterialDesignIcon icon-name="magnify" class="size-5 text-gray-400" />
                    </div>
                    <input
                        v-model="searchQuery"
                        type="text"
                        class="block w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-zinc-700 rounded-lg bg-gray-50 dark:bg-zinc-800 text-gray-900 dark:text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                        placeholder="Search by hash or display name..."
                        @input="onSearchInput"
                    />
                </div>
                <button
                    class="p-2 text-gray-500 hover:text-blue-500 dark:text-gray-400 dark:hover:text-blue-400 transition-colors"
                    title="Refresh"
                    @click="loadBlockedDestinations"
                >
                    <MaterialDesignIcon icon-name="refresh" class="size-6" :class="{ 'animate-spin': isLoading }" />
                </button>
            </div>
        </div>

        <div class="flex-1 overflow-y-auto p-4 md:p-6">
            <div v-if="isLoading && blockedItems.length === 0" class="flex flex-col items-center justify-center h-64">
                <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mb-4"></div>
                <p class="text-gray-500 dark:text-gray-400">Loading blocked items...</p>
            </div>

            <div
                v-else-if="filteredBlockedItems.length === 0"
                class="flex flex-col items-center justify-center h-64 text-center"
            >
                <div class="p-4 bg-gray-100 dark:bg-zinc-800 rounded-full mb-4 text-gray-400 dark:text-zinc-600">
                    <MaterialDesignIcon icon-name="check-circle" class="size-12" />
                </div>
                <h3 class="text-lg font-medium text-gray-900 dark:text-white">No blocked items</h3>
                <p class="text-gray-500 dark:text-gray-400 max-w-sm mx-auto">
                    {{
                        searchQuery
                            ? "No blocked items match your search."
                            : "You haven't blocked any users or nodes yet."
                    }}
                </p>
            </div>

            <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div
                    v-for="item in filteredBlockedItems"
                    :key="item.destination_hash"
                    class="bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 rounded-xl shadow-lg overflow-hidden"
                >
                    <div class="p-5">
                        <div class="flex items-start justify-between mb-4">
                            <div class="flex-1 min-w-0">
                                <div class="flex items-center gap-2 mb-2">
                                    <div class="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg flex-shrink-0">
                                        <MaterialDesignIcon
                                            icon-name="account-off"
                                            class="size-5 text-red-600 dark:text-red-400"
                                        />
                                    </div>
                                    <div class="min-w-0 flex-1">
                                        <div class="flex items-center gap-2 mb-1">
                                            <h4
                                                class="text-base font-semibold text-gray-900 dark:text-white break-words"
                                                :title="item.display_name"
                                            >
                                                {{ item.display_name || "Unknown" }}
                                            </h4>
                                            <span
                                                v-if="item.is_node"
                                                class="px-2 py-0.5 text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded"
                                            >
                                                Node
                                            </span>
                                            <span
                                                v-else
                                                class="px-2 py-0.5 text-xs font-medium bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded"
                                            >
                                                User
                                            </span>
                                        </div>
                                        <p
                                            class="text-xs text-gray-500 dark:text-gray-400 font-mono break-all mt-1"
                                            :title="item.destination_hash"
                                        >
                                            {{ item.destination_hash }}
                                        </p>
                                    </div>
                                </div>
                                <div class="text-xs text-gray-500 dark:text-gray-400">
                                    Blocked {{ formatTimeAgo(item.created_at) }}
                                </div>
                            </div>
                        </div>
                        <button
                            class="w-full flex items-center justify-center gap-2 px-4 py-2 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-300 rounded-lg hover:bg-green-100 dark:hover:bg-green-900/30 transition-colors font-medium"
                            @click="onUnblock(item)"
                        >
                            <MaterialDesignIcon icon-name="check-circle" class="size-5" />
                            <span>Unblock</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import DialogUtils from "../../js/DialogUtils";
import ToastUtils from "../../js/ToastUtils";
import Utils from "../../js/Utils";

export default {
    name: "BlockedPage",
    components: {
        MaterialDesignIcon,
    },
    data() {
        return {
            blockedItems: [],
            isLoading: false,
            searchQuery: "",
        };
    },
    computed: {
        filteredBlockedItems() {
            if (!this.searchQuery.trim()) {
                return this.blockedItems;
            }
            const query = this.searchQuery.toLowerCase();
            return this.blockedItems.filter((item) => {
                const matchesHash = item.destination_hash.toLowerCase().includes(query);
                const matchesDisplayName = (item.display_name || "").toLowerCase().includes(query);
                return matchesHash || matchesDisplayName;
            });
        },
    },
    mounted() {
        this.loadBlockedDestinations();
    },
    methods: {
        async loadBlockedDestinations() {
            this.isLoading = true;
            try {
                const response = await window.axios.get("/api/v1/blocked-destinations");
                const blockedHashes = response.data.blocked_destinations || [];

                const items = await Promise.all(
                    blockedHashes.map(async (blocked) => {
                        let displayName = "Unknown";
                        let isNode = false;

                        try {
                            const nodeAnnounceResponse = await window.axios.get("/api/v1/announces", {
                                params: {
                                    aspect: "nomadnetwork.node",
                                    identity_hash: blocked.destination_hash,
                                    include_blocked: true,
                                    limit: 1,
                                },
                            });

                            if (nodeAnnounceResponse.data.announces && nodeAnnounceResponse.data.announces.length > 0) {
                                const announce = nodeAnnounceResponse.data.announces[0];
                                displayName = announce.display_name || "Unknown";
                                isNode = true;
                            } else {
                                const announceResponse = await window.axios.get("/api/v1/announces", {
                                    params: {
                                        identity_hash: blocked.destination_hash,
                                        include_blocked: true,
                                        limit: 1,
                                    },
                                });

                                if (announceResponse.data.announces && announceResponse.data.announces.length > 0) {
                                    const announce = announceResponse.data.announces[0];
                                    displayName = announce.display_name || "Unknown";
                                    isNode = announce.aspect === "nomadnetwork.node";
                                } else {
                                    const lxmfResponse = await window.axios.get("/api/v1/announces", {
                                        params: {
                                            destination_hash: blocked.destination_hash,
                                            include_blocked: true,
                                            limit: 1,
                                        },
                                    });

                                    if (lxmfResponse.data.announces && lxmfResponse.data.announces.length > 0) {
                                        const announce = lxmfResponse.data.announces[0];
                                        displayName = announce.display_name || "Unknown";
                                        isNode = announce.aspect === "nomadnetwork.node";
                                    }
                                }
                            }
                        } catch (e) {
                            console.log(e);
                        }

                        return {
                            destination_hash: blocked.destination_hash,
                            display_name: displayName,
                            created_at: blocked.created_at,
                            is_node: isNode,
                        };
                    })
                );

                this.blockedItems = items;
            } catch (e) {
                console.log(e);
                ToastUtils.error("Failed to load blocked destinations");
            } finally {
                this.isLoading = false;
            }
        },
        async onUnblock(item) {
            if (
                !(await DialogUtils.confirm(
                    `Are you sure you want to unblock ${item.display_name || item.destination_hash}?`
                ))
            ) {
                return;
            }

            try {
                await window.axios.delete(`/api/v1/blocked-destinations/${item.destination_hash}`);
                await this.loadBlockedDestinations();
                ToastUtils.success("Unblocked successfully");
            } catch (e) {
                console.log(e);
                ToastUtils.error("Failed to unblock");
            }
        },
        onSearchInput() {},
        formatDestinationHash: function (destinationHash) {
            return Utils.formatDestinationHash(destinationHash);
        },
        formatTimeAgo: function (datetimeString) {
            return Utils.formatTimeAgo(datetimeString);
        },
    },
};
</script>
