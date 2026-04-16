<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-gray-50 dark:bg-zinc-950">
        <div class="px-4 py-4 border-b border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
            <div class="rounded-2xl border border-gray-200 dark:border-zinc-800 p-4">
                <div class="flex flex-col gap-3">
                    <div class="flex flex-wrap items-center gap-2">
                        <div class="font-semibold text-gray-900 dark:text-zinc-100">Hosted Propagation Node</div>
                        <span
                            v-if="localPropagationNode"
                            class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold"
                            :class="
                                localPropagationNode.is_propagation_enabled
                                    ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                                    : 'bg-gray-100 text-gray-700 dark:bg-zinc-800 dark:text-zinc-300'
                            "
                        >
                            {{ localPropagationNode.is_propagation_enabled ? "Running" : "Stopped" }}
                        </span>
                        <span
                            v-if="
                                localPropagationNode &&
                                config.lxmf_preferred_propagation_node_destination_hash ===
                                    localPropagationNode.destination_hash
                            "
                            class="inline-flex items-center gap-1 rounded-full bg-blue-100 dark:bg-blue-900/30 px-2 py-0.5 text-xs font-semibold text-blue-700 dark:text-blue-300"
                        >
                            Preferred
                        </span>
                    </div>
                    <div
                        v-if="config.lxmf_local_propagation_node_address_hash"
                        class="text-xs font-mono text-gray-600 dark:text-zinc-400 break-all"
                    >
                        &lt;{{ config.lxmf_local_propagation_node_address_hash }}&gt;
                    </div>
                    <div
                        v-if="localPropagationNode?.local_node_stats"
                        class="text-xs text-gray-600 dark:text-zinc-400 flex flex-wrap gap-x-3 gap-y-1"
                    >
                        <span>{{ formatSeconds(localPropagationNode.local_node_stats.uptime_seconds) }} uptime</span>
                        <span>{{ localPropagationNode.local_node_stats.total_peers }} peers</span>
                        <span>{{ localPropagationNode.local_node_stats.messagestore_count }} messages stored</span>
                        <span>{{ localPropagationNode.local_node_stats.client_messages_served }} served</span>
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
                        <label class="text-xs text-gray-600 dark:text-zinc-400">
                            Delivery transfer limit (bytes)
                            <input
                                v-model.number="config.lxmf_delivery_transfer_limit_in_bytes"
                                type="number"
                                min="1000"
                                class="mt-1 w-full bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 text-gray-900 dark:text-zinc-100 text-sm rounded-xl px-3 py-2"
                                @input="onDeliveryTransferLimitChange"
                            />
                        </label>
                        <label class="text-xs text-gray-600 dark:text-zinc-400">
                            Propagation transfer limit (bytes)
                            <input
                                v-model.number="config.lxmf_propagation_transfer_limit_in_bytes"
                                type="number"
                                min="1000"
                                class="mt-1 w-full bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 text-gray-900 dark:text-zinc-100 text-sm rounded-xl px-3 py-2"
                                @input="onPropagationTransferLimitChange"
                            />
                        </label>
                        <label class="text-xs text-gray-600 dark:text-zinc-400">
                            Propagation sync limit (bytes)
                            <input
                                v-model.number="config.lxmf_propagation_sync_limit_in_bytes"
                                type="number"
                                min="1000"
                                class="mt-1 w-full bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 text-gray-900 dark:text-zinc-100 text-sm rounded-xl px-3 py-2"
                                @input="onPropagationSyncLimitChange"
                            />
                        </label>
                    </div>
                    <div class="flex flex-wrap gap-2">
                        <button
                            type="button"
                            class="inline-flex items-center gap-x-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors"
                            :disabled="!localPropagationNode"
                            @click="useLocalPropagationNode"
                        >
                            Use Our Node
                        </button>
                        <button
                            type="button"
                            class="inline-flex items-center gap-x-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors"
                            @click="restartLocalPropagationNode"
                        >
                            Restart Node
                        </button>
                        <button
                            type="button"
                            class="inline-flex items-center gap-x-1.5 rounded-xl bg-red-600 hover:bg-red-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors"
                            @click="stopLocalPropagationNode"
                        >
                            Stop Node
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- search and sort -->
        <div
            v-if="propagationNodes.length > 0"
            class="flex flex-col sm:flex-row gap-2 bg-white dark:bg-zinc-900 border-b border-gray-200 dark:border-zinc-800 px-4 py-3"
        >
            <input
                v-model="searchTerm"
                type="text"
                :placeholder="`Search ${propagationNodes.length} Propagation Nodes...`"
                class="flex-1 bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 text-gray-900 dark:text-zinc-100 text-sm rounded-xl focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 px-4 py-2 shadow-sm transition-all placeholder:text-gray-400 dark:placeholder:text-zinc-500"
            />
            <select
                v-model="sortBy"
                class="bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 text-gray-900 dark:text-zinc-100 text-sm rounded-xl focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 px-4 py-2 shadow-sm transition-all min-w-[180px]"
            >
                <option value="name">Sort by Name</option>
                <option value="name-desc">Sort by Name (Z-A)</option>
                <option value="recent">Sort by Recent</option>
                <option value="oldest">Sort by Oldest</option>
                <option value="preferred">Preferred First</option>
            </select>
        </div>

        <!-- propagation nodes -->
        <div class="h-full overflow-y-auto px-4 py-4">
            <div v-if="paginatedNodes.length > 0" class="space-y-3 w-full">
                <div
                    v-for="propagationNode of paginatedNodes"
                    :key="propagationNode.destination_hash"
                    class="border border-gray-200 dark:border-zinc-800 rounded-2xl bg-white dark:bg-zinc-900 shadow-sm hover:shadow-md transition-shadow overflow-hidden"
                    :class="{
                        'ring-2 ring-blue-500 dark:ring-blue-400':
                            config.lxmf_preferred_propagation_node_destination_hash ===
                            propagationNode.destination_hash,
                    }"
                >
                    <div class="p-4 flex items-center gap-3">
                        <div class="flex-1 min-w-0">
                            <div class="flex items-center gap-2 mb-1">
                                <div class="font-semibold text-gray-900 dark:text-zinc-100 truncate">
                                    {{ propagationNode.operator_display_name ?? "Unknown Operator" }}
                                </div>
                                <span
                                    v-if="
                                        config.lxmf_preferred_propagation_node_destination_hash ===
                                        propagationNode.destination_hash
                                    "
                                    class="inline-flex items-center gap-1 rounded-full bg-blue-100 dark:bg-blue-900/30 px-2 py-0.5 text-xs font-semibold text-blue-700 dark:text-blue-300"
                                >
                                    <svg
                                        xmlns="http://www.w3.org/2000/svg"
                                        viewBox="0 0 20 20"
                                        fill="currentColor"
                                        class="w-3 h-3"
                                    >
                                        <path
                                            fill-rule="evenodd"
                                            d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm3.857-9.809a.75.75 0 0 0-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 1 0-1.06 1.061l2.5 2.5a.75.75 0 0 0 1.137-.089l4-5.5Z"
                                            clip-rule="evenodd"
                                        />
                                    </svg>
                                    Preferred
                                </span>
                                <span
                                    v-if="propagationNode.is_propagation_enabled === false"
                                    class="inline-flex items-center gap-1 rounded-full bg-red-100 dark:bg-red-900/30 px-2 py-0.5 text-xs font-semibold text-red-700 dark:text-red-300"
                                >
                                    Disabled
                                </span>
                                <span
                                    v-if="propagationNode.is_local_node"
                                    class="inline-flex items-center gap-1 rounded-full bg-emerald-100 dark:bg-emerald-900/30 px-2 py-0.5 text-xs font-semibold text-emerald-700 dark:text-emerald-300"
                                >
                                    Our Node
                                </span>
                            </div>
                            <div class="text-sm text-gray-600 dark:text-zinc-400 font-mono truncate">
                                &lt;{{ propagationNode.destination_hash }}&gt;
                            </div>
                            <div class="text-xs text-gray-500 dark:text-zinc-500 mt-1">
                                Announced {{ formatTimeAgo(propagationNode.updated_at) }}
                            </div>
                            <div
                                v-if="propagationNode.local_node_stats"
                                class="text-xs text-gray-500 dark:text-zinc-500 mt-1 flex flex-wrap gap-x-3 gap-y-1"
                            >
                                <span>{{ formatSeconds(propagationNode.local_node_stats.uptime_seconds) }} uptime</span>
                                <span>{{ propagationNode.local_node_stats.total_peers }} peers</span>
                                <span>{{ propagationNode.local_node_stats.messagestore_count }} stored</span>
                                <span>{{ propagationNode.local_node_stats.client_messages_served }} served</span>
                            </div>
                        </div>
                        <div class="flex-shrink-0">
                            <button
                                v-if="
                                    config.lxmf_preferred_propagation_node_destination_hash ===
                                    propagationNode.destination_hash
                                "
                                type="button"
                                class="inline-flex items-center gap-x-1.5 rounded-xl bg-red-600 hover:bg-red-700 dark:bg-red-600 dark:hover:bg-red-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500"
                                @click="stopUsingPropagationNode"
                            >
                                Stop Using
                            </button>
                            <button
                                v-else
                                type="button"
                                class="inline-flex items-center gap-x-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 dark:bg-blue-600 dark:hover:bg-blue-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500"
                                @click="usePropagationNode(propagationNode.destination_hash)"
                            >
                                Set as Preferred
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- pagination -->
            <div
                v-if="totalPages > 1"
                class="flex items-center justify-between mt-6 pt-4 border-t border-gray-200 dark:border-zinc-800"
            >
                <div class="text-sm text-gray-600 dark:text-zinc-400">
                    Showing {{ startIndex + 1 }}-{{ endIndex }} of {{ sortedAndSearchedPropagationNodes.length }}
                </div>
                <div class="flex items-center gap-2">
                    <button
                        :disabled="currentPage === 1"
                        type="button"
                        class="inline-flex items-center gap-x-1.5 rounded-xl bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 hover:bg-gray-50 dark:hover:bg-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed px-3 py-2 text-sm font-medium text-gray-700 dark:text-zinc-300 shadow-sm transition-colors"
                        @click="currentPage = Math.max(1, currentPage - 1)"
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke-width="1.5"
                            stroke="currentColor"
                            class="w-4 h-4"
                        >
                            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
                        </svg>
                        Previous
                    </button>
                    <div class="flex items-center gap-1">
                        <button
                            v-for="page in visiblePages"
                            :key="page"
                            type="button"
                            :class="[
                                page === currentPage
                                    ? 'bg-blue-600 text-white dark:bg-blue-600'
                                    : 'bg-white dark:bg-zinc-900 text-gray-700 dark:text-zinc-300 hover:bg-gray-50 dark:hover:bg-zinc-800',
                            ]"
                            class="w-10 h-10 rounded-xl border border-gray-200 dark:border-zinc-800 text-sm font-medium shadow-sm transition-colors"
                            @click="currentPage = page"
                        >
                            {{ page }}
                        </button>
                    </div>
                    <button
                        :disabled="currentPage === totalPages"
                        type="button"
                        class="inline-flex items-center gap-x-1.5 rounded-xl bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 hover:bg-gray-50 dark:hover:bg-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed px-3 py-2 text-sm font-medium text-gray-700 dark:text-zinc-300 shadow-sm transition-colors"
                        @click="currentPage = Math.min(totalPages, currentPage + 1)"
                    >
                        Next
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke-width="1.5"
                            stroke="currentColor"
                            class="w-4 h-4"
                        >
                            <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                        </svg>
                    </button>
                </div>
            </div>

            <div v-else-if="sortedAndSearchedPropagationNodes.length === 0" class="flex h-full">
                <div class="mx-auto my-auto text-center leading-5 text-gray-900 dark:text-gray-100">
                    <!-- no propagation nodes at all -->
                    <div v-if="propagationNodes.length === 0" class="flex flex-col">
                        <div class="mx-auto mb-1">
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke-width="1.5"
                                stroke="currentColor"
                                class="size-6"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M2.25 13.5h3.86a2.25 2.25 0 0 1 2.012 1.244l.256.512a2.25 2.25 0 0 0 2.013 1.244h3.218a2.25 2.25 0 0 0 2.013-1.244l.256-.512a2.25 2.25 0 0 1 2.013-1.244h3.859m-19.5.338V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18v-4.162c0-.224-.034-.447-.1-.661L19.24 5.338a2.25 2.25 0 0 0-2.15-1.588H6.911a2.25 2.25 0 0 0-2.15 1.588L2.35 13.177a2.25 2.25 0 0 0-.1.661Z"
                                />
                            </svg>
                        </div>
                        <div class="font-semibold">No Propagation Nodes</div>
                        <div>Check back later, once someone has announced.</div>
                        <div class="mt-4">
                            <button
                                type="button"
                                class="inline-flex items-center gap-x-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 dark:bg-blue-600 dark:hover:bg-blue-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500"
                                @click="loadPropagationNodes"
                            >
                                Reload
                            </button>
                        </div>
                    </div>

                    <!-- is searching, but no results -->
                    <div v-if="searchTerm !== '' && propagationNodes.length > 0" class="flex flex-col">
                        <div class="mx-auto mb-1">
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke-width="1.5"
                                stroke="currentColor"
                                class="w-6 h-6"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
                                />
                            </svg>
                        </div>
                        <div class="font-semibold">No Search Results</div>
                        <div>Your search didn't match any Propagation Nodes!</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import Utils from "../../js/Utils";
import WebSocketConnection from "../../js/WebSocketConnection";
import ToastUtils from "../../js/ToastUtils";

export default {
    name: "PropagationNodesPage",
    data() {
        return {
            searchTerm: "",
            sortBy: "preferred",
            propagationNodes: [],
            config: {
                lxmf_preferred_propagation_node_destination_hash: null,
                lxmf_local_propagation_node_address_hash: null,
                lxmf_delivery_transfer_limit_in_bytes: 1000 * 1000 * 10,
                lxmf_propagation_transfer_limit_in_bytes: 1000 * 256,
                lxmf_propagation_sync_limit_in_bytes: 1000 * 10240,
            },
            currentPage: 1,
            itemsPerPage: 20,
            saveTimeouts: {
                deliveryLimit: null,
                propagationLimit: null,
                propagationSyncLimit: null,
            },
        };
    },
    computed: {
        localPropagationNode() {
            return this.propagationNodes.find((node) => node.is_local_node) ?? null;
        },
        searchedPropagationNodes() {
            return this.propagationNodes.filter((propagationNode) => {
                const search = this.searchTerm.toLowerCase();
                const matchesOperatorDisplayName =
                    propagationNode.operator_display_name?.toLowerCase()?.includes(search) ?? false;
                const matchesDestinationHash = propagationNode.destination_hash.toLowerCase().includes(search);
                return matchesOperatorDisplayName || matchesDestinationHash;
            });
        },
        sortedAndSearchedPropagationNodes() {
            let nodes = [...this.searchedPropagationNodes];

            switch (this.sortBy) {
                case "name":
                    nodes.sort((a, b) => {
                        const nameA = (a.operator_display_name ?? "Unknown Operator").toLowerCase();
                        const nameB = (b.operator_display_name ?? "Unknown Operator").toLowerCase();
                        return nameA.localeCompare(nameB);
                    });
                    break;
                case "name-desc":
                    nodes.sort((a, b) => {
                        const nameA = (a.operator_display_name ?? "Unknown Operator").toLowerCase();
                        const nameB = (b.operator_display_name ?? "Unknown Operator").toLowerCase();
                        return nameB.localeCompare(nameA);
                    });
                    break;
                case "recent":
                    nodes.sort((a, b) => {
                        const timeA = new Date(a.updated_at).getTime();
                        const timeB = new Date(b.updated_at).getTime();
                        return timeB - timeA;
                    });
                    break;
                case "oldest":
                    nodes.sort((a, b) => {
                        const timeA = new Date(a.updated_at).getTime();
                        const timeB = new Date(b.updated_at).getTime();
                        return timeA - timeB;
                    });
                    break;
                case "preferred":
                default:
                    nodes.sort((a, b) => {
                        const aIsPreferred =
                            this.config.lxmf_preferred_propagation_node_destination_hash === a.destination_hash;
                        const bIsPreferred =
                            this.config.lxmf_preferred_propagation_node_destination_hash === b.destination_hash;
                        if (aIsPreferred && !bIsPreferred) return -1;
                        if (!aIsPreferred && bIsPreferred) return 1;
                        if (a.is_local_node && !b.is_local_node) return -1;
                        if (!a.is_local_node && b.is_local_node) return 1;
                        const timeA = new Date(a.updated_at).getTime();
                        const timeB = new Date(b.updated_at).getTime();
                        return timeB - timeA;
                    });
                    break;
            }

            return nodes;
        },
        totalPages() {
            return Math.ceil(this.sortedAndSearchedPropagationNodes.length / this.itemsPerPage);
        },
        startIndex() {
            return (this.currentPage - 1) * this.itemsPerPage;
        },
        endIndex() {
            return Math.min(this.startIndex + this.itemsPerPage, this.sortedAndSearchedPropagationNodes.length);
        },
        paginatedNodes() {
            return this.sortedAndSearchedPropagationNodes.slice(this.startIndex, this.endIndex);
        },
        visiblePages() {
            const pages = [];
            const maxVisible = 5;
            let start = Math.max(1, this.currentPage - Math.floor(maxVisible / 2));
            let end = Math.min(this.totalPages, start + maxVisible - 1);
            if (end - start < maxVisible - 1) {
                start = Math.max(1, end - maxVisible + 1);
            }
            for (let i = start; i <= end; i++) {
                pages.push(i);
            }
            return pages;
        },
    },
    watch: {
        searchTerm() {
            this.currentPage = 1;
        },
        sortBy() {
            this.currentPage = 1;
        },
    },
    beforeUnmount() {
        // stop listening for websocket messages
        WebSocketConnection.off("message", this.onWebsocketMessage);
        for (const timeoutKey of Object.keys(this.saveTimeouts)) {
            if (this.saveTimeouts[timeoutKey]) {
                clearTimeout(this.saveTimeouts[timeoutKey]);
            }
        }
    },
    mounted() {
        // listen for websocket messages
        WebSocketConnection.on("message", this.onWebsocketMessage);

        this.getConfig();
        this.loadPropagationNodes();
    },
    methods: {
        async onWebsocketMessage(message) {
            const json = JSON.parse(message.data);
            switch (json.type) {
                case "config": {
                    this.config = json.config;
                    break;
                }
            }
        },
        async getConfig() {
            try {
                const response = await window.api.get("/api/v1/config");
                this.config = response.data.config;
            } catch (e) {
                // do nothing if failed to load config
                console.log(e);
            }
        },
        async updateConfig(config) {
            try {
                const response = await window.api.patch("/api/v1/config", config);
                this.config = response.data.config;
            } catch (e) {
                ToastUtils.error(this.$t("common.save_failed"));
                console.log(e);
            }
        },
        async loadPropagationNodes() {
            try {
                const response = await window.api.get(`/api/v1/lxmf/propagation-nodes`, {
                    params: {
                        limit: 500,
                    },
                });
                this.propagationNodes = response.data.lxmf_propagation_nodes;
            } catch {
                // do nothing if failed to load
            }
        },
        async usePropagationNode(destination_hash) {
            await this.updateConfig({
                lxmf_preferred_propagation_node_destination_hash: destination_hash,
            });
        },
        async stopUsingPropagationNode() {
            await this.updateConfig({
                lxmf_preferred_propagation_node_destination_hash: null,
            });
        },
        async useLocalPropagationNode() {
            if (!this.localPropagationNode) return;
            await this.usePropagationNode(this.localPropagationNode.destination_hash);
        },
        async restartLocalPropagationNode() {
            try {
                await window.api.post("/api/v1/lxmf/propagation-node/restart");
                ToastUtils.success("Local propagation node restarted");
                await Promise.all([this.getConfig(), this.loadPropagationNodes()]);
            } catch {
                ToastUtils.error(this.$t("common.save_failed"));
            }
        },
        async stopLocalPropagationNode() {
            try {
                await window.api.post("/api/v1/lxmf/propagation-node/stop");
                ToastUtils.success("Local propagation node stopped");
                await Promise.all([this.getConfig(), this.loadPropagationNodes()]);
            } catch {
                ToastUtils.error(this.$t("common.save_failed"));
            }
        },
        onDeliveryTransferLimitChange() {
            if (this.saveTimeouts.deliveryLimit) clearTimeout(this.saveTimeouts.deliveryLimit);
            this.saveTimeouts.deliveryLimit = setTimeout(async () => {
                await this.updateConfig({
                    lxmf_delivery_transfer_limit_in_bytes: this.config.lxmf_delivery_transfer_limit_in_bytes,
                });
            }, 450);
        },
        onPropagationTransferLimitChange() {
            if (this.saveTimeouts.propagationLimit) clearTimeout(this.saveTimeouts.propagationLimit);
            this.saveTimeouts.propagationLimit = setTimeout(async () => {
                await this.updateConfig({
                    lxmf_propagation_transfer_limit_in_bytes: this.config.lxmf_propagation_transfer_limit_in_bytes,
                });
            }, 450);
        },
        onPropagationSyncLimitChange() {
            if (this.saveTimeouts.propagationSyncLimit) clearTimeout(this.saveTimeouts.propagationSyncLimit);
            this.saveTimeouts.propagationSyncLimit = setTimeout(async () => {
                await this.updateConfig({
                    lxmf_propagation_sync_limit_in_bytes: this.config.lxmf_propagation_sync_limit_in_bytes,
                });
            }, 450);
        },
        formatTimeAgo: function (datetimeString) {
            return Utils.formatTimeAgo(datetimeString);
        },
        formatSeconds(seconds) {
            if (seconds == null || Number.isNaN(Number(seconds))) return "0s";
            const total = Math.max(0, Number(seconds));
            if (total < 60) return `${Math.floor(total)}s`;
            const minutes = Math.floor(total / 60);
            if (minutes < 60) return `${minutes}m`;
            const hours = Math.floor(minutes / 60);
            if (hours < 24) return `${hours}h`;
            const days = Math.floor(hours / 24);
            return `${days}d`;
        },
    },
};
</script>
