<template>
    <div class="flex flex-col flex-1 h-full overflow-hidden bg-white dark:bg-zinc-950">
        <!-- header -->
        <div
            class="flex flex-wrap items-center gap-2 px-3 sm:px-4 py-3 sm:py-4 bg-white dark:bg-zinc-950 border-b border-gray-200 dark:border-zinc-800"
        >
            <div class="flex items-center gap-2 sm:gap-3 min-w-0 flex-1">
                <div class="p-2 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg shrink-0">
                    <MaterialDesignIcon icon-name="route" class="size-5 sm:size-6 text-indigo-600 dark:text-indigo-400" />
                </div>
                <div class="min-w-0">
                    <h1 class="text-lg sm:text-xl font-bold text-gray-900 dark:text-white truncate">RNPath</h1>
                    <p class="text-xs sm:text-sm text-gray-500 dark:text-gray-400 line-clamp-2 sm:line-clamp-none">
                        Reticulum Path Management Utility
                    </p>
                </div>
            </div>

            <div class="ml-auto flex items-center gap-2 shrink-0">
                <button
                    class="p-2 text-gray-500 hover:text-indigo-500 dark:text-gray-400 dark:hover:text-indigo-400 transition-colors"
                    title="Refresh"
                    @click="refreshAll"
                >
                    <MaterialDesignIcon
                        icon-name="refresh"
                        class="size-6"
                        :class="{ 'animate-spin-reverse': isLoading }"
                    />
                </button>
            </div>
        </div>

        <div class="flex-1 overflow-y-auto p-3 sm:p-4 md:p-6 space-y-4 sm:space-y-6">
            <!-- tabs -->
            <div class="-mx-3 sm:mx-0 overflow-x-auto border-b border-gray-200 dark:border-zinc-800">
                <div class="flex min-w-0 px-3 sm:px-0">
                    <button
                        v-for="t in ['table', 'rates', 'actions']"
                        :key="t"
                        type="button"
                        class="shrink-0 px-4 sm:px-6 py-3 text-sm font-semibold transition-colors border-b-2 -mb-px"
                        :class="[
                            tab === t
                                ? 'text-indigo-600 border-indigo-500 dark:text-indigo-400 dark:border-indigo-400'
                                : 'text-gray-500 border-transparent hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200',
                        ]"
                        @click="tab = t"
                    >
                        {{ t.charAt(0).toUpperCase() + t.slice(1) }}
                    </button>
                </div>
            </div>

            <!-- path table -->
            <div v-if="tab === 'table'" class="space-y-4">
                <!-- filters -->
                <div
                    class="rounded-lg border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-3 sm:p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4"
                >
                    <div class="relative">
                        <input
                            v-model="searchQuery"
                            type="text"
                            placeholder="Search Hash or Via..."
                            class="input-field pr-10"
                            autocomplete="off"
                        />
                        <MaterialDesignIcon
                            icon-name="magnify"
                            class="pointer-events-none absolute right-3 top-1/2 size-5 -translate-y-1/2 text-gray-400"
                            aria-hidden="true"
                        />
                    </div>
                    <select v-model="filterInterface" class="input-field">
                        <option value="">All Interfaces</option>
                        <option v-for="iface in interfaces" :key="iface" :value="iface">
                            {{ iface }}
                        </option>
                    </select>
                    <div class="flex items-center gap-2">
                        <span class="text-xs font-semibold text-gray-500 uppercase min-w-fit">Hops:</span>
                        <input
                            v-model.number="filterHops"
                            type="number"
                            min="0"
                            max="128"
                            placeholder="Any"
                            class="input-field"
                        />
                    </div>
                    <div
                        class="flex flex-wrap items-center justify-start sm:justify-end gap-x-4 gap-y-2 sm:flex-nowrap lg:col-span-1"
                    >
                        <div class="flex flex-col items-start sm:items-end">
                            <span class="text-[10px] font-bold text-gray-400 uppercase">Total</span>
                            <span class="text-sm font-bold">{{ totalItems }}</span>
                        </div>
                        <div class="flex flex-col items-start sm:items-end">
                            <span class="text-[10px] font-bold text-green-500 uppercase">Responsive</span>
                            <span class="text-sm font-bold text-green-600 dark:text-green-400">{{
                                responsiveItems
                            }}</span>
                        </div>
                        <div class="flex flex-col items-start sm:items-end">
                            <span class="text-[10px] font-bold text-red-500 uppercase">Unresponsive</span>
                            <span class="text-sm font-bold text-red-600 dark:text-red-400">{{
                                unresponsiveItems
                            }}</span>
                        </div>
                    </div>
                </div>

                <div
                    v-if="pathTable.length === 0"
                    class="rounded-lg border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-8 sm:p-12 text-center text-gray-500"
                >
                    No paths found matching your criteria.
                </div>
                <div v-else class="grid gap-4">
                    <div
                        v-for="path in pathTable"
                        :key="path.hash"
                        class="rounded-lg border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-3 sm:p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-l-4"
                        :class="[
                            path.state === 2
                                ? 'border-l-green-500'
                                : path.state === 1
                                  ? 'border-l-red-500'
                                  : 'border-l-gray-300 dark:border-l-zinc-700',
                        ]"
                    >
                        <div class="min-w-0">
                            <div class="flex flex-wrap items-center gap-2 mb-1">
                                <span class="font-mono text-sm font-bold text-indigo-600 dark:text-indigo-400 truncate">
                                    {{ path.hash }}
                                </span>
                                <span
                                    class="px-2 py-0.5 text-[10px] font-bold bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded uppercase tracking-wider"
                                >
                                    {{ path.hops }} {{ path.hops === 1 ? "hop" : "hops" }}
                                </span>
                                <span
                                    class="px-2 py-0.5 text-[10px] font-bold rounded uppercase tracking-wider"
                                    :class="getStateColor(path.state)"
                                >
                                    {{ getStateText(path.state) }}
                                </span>
                            </div>
                            <div class="text-xs text-gray-500 dark:text-gray-400 font-mono truncate">
                                via {{ path.via }} on {{ path.interface }}
                            </div>
                            <div class="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-[10px]">
                                <div class="text-gray-400">
                                    <span class="font-semibold uppercase">Last Updated:</span>
                                    {{ path.timestamp ? formatDate(path.timestamp) : "Unknown" }}
                                </div>
                                <div class="text-gray-400">
                                    <span class="font-semibold uppercase">Expires:</span> {{ formatDate(path.expires) }}
                                </div>
                                <div v-if="path.announce_hash" class="text-gray-400">
                                    <span class="font-semibold uppercase">Announce Hash:</span> {{ path.announce_hash }}
                                </div>
                            </div>
                        </div>
                        <button
                            class="px-3 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20 rounded-lg transition-colors border border-red-200 dark:border-red-900/30"
                            @click="dropPath(path.hash)"
                        >
                            Drop Path
                        </button>
                    </div>
                </div>

                <!-- pagination -->
                <div
                    v-if="totalPages > 1"
                    class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-lg border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-3 sm:p-4"
                >
                    <div class="flex items-center gap-2">
                        <button
                            class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-zinc-800 disabled:opacity-50 transition-colors"
                            :disabled="currentPage === 1"
                            @click="currentPage--"
                        >
                            <MaterialDesignIcon icon-name="chevron-left" class="size-5" />
                        </button>
                        <span class="text-sm font-medium"> Page {{ currentPage }} of {{ totalPages }} </span>
                        <button
                            class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-zinc-800 disabled:opacity-50 transition-colors"
                            :disabled="currentPage === totalPages"
                            @click="currentPage++"
                        >
                            <MaterialDesignIcon icon-name="chevron-right" class="size-5" />
                        </button>
                    </div>
                    <div class="flex items-center gap-2 justify-between sm:justify-end w-full sm:w-auto">
                        <span class="text-xs text-gray-500 uppercase font-semibold">Show:</span>
                        <select
                            v-model="itemsPerPage"
                            class="bg-transparent border-none text-sm font-bold focus:ring-0 cursor-pointer"
                        >
                            <option :value="20">20</option>
                            <option :value="50">50</option>
                            <option :value="100">100</option>
                            <option :value="250">250</option>
                        </select>
                    </div>
                </div>
            </div>

            <!-- announce rates -->
            <div v-if="tab === 'rates'" class="space-y-4">
                <div
                    v-if="rateTable.length === 0"
                    class="rounded-lg border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-8 sm:p-12 text-center text-gray-500"
                >
                    No announce rate data available.
                </div>
                <div v-else class="grid gap-4">
                    <div
                        v-for="rate in rateTable"
                        :key="rate.hash"
                        class="rounded-lg border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-3 sm:p-4"
                    >
                        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
                            <span class="font-mono text-sm font-bold text-indigo-600 dark:text-indigo-400 truncate">
                                {{ rate.hash }}
                            </span>
                            <span
                                v-if="rate.blocked_until > Date.now() / 1000"
                                class="px-2 py-0.5 text-[10px] font-bold bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded"
                            >
                                RATE LIMITED
                            </span>
                        </div>
                        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
                            <div>
                                <div class="text-[10px] uppercase text-gray-500">Last Heard</div>
                                <div class="text-xs font-medium">{{ formatTimeAgo(rate.last) }}</div>
                            </div>
                            <div>
                                <div class="text-[10px] uppercase text-gray-500">Announces</div>
                                <div class="text-xs font-medium">{{ rate.timestamps.length }}</div>
                            </div>
                            <div>
                                <div class="text-[10px] uppercase text-gray-500">Violations</div>
                                <div
                                    class="text-xs font-medium"
                                    :class="rate.rate_violations > 0 ? 'text-red-500' : ''"
                                >
                                    {{ rate.rate_violations }}
                                </div>
                            </div>
                            <div>
                                <div class="text-[10px] uppercase text-gray-500">Rate</div>
                                <div class="text-xs font-medium">{{ calculateRate(rate) }} / hr</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- manual actions -->
            <div v-if="tab === 'actions'" class="max-w-2xl mx-auto space-y-6">
                <!-- request path -->
                <section class="rounded-lg border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4 sm:p-6 space-y-4">
                    <h2 class="text-lg font-bold">Request Path</h2>
                    <p class="text-sm text-gray-500">Broadcast a path request for a destination hash.</p>
                    <div class="flex flex-col sm:flex-row gap-2">
                        <input
                            v-model="requestHash"
                            type="text"
                            placeholder="Destination Hash (32 hex chars)"
                            class="input-field flex-1 min-w-0 font-mono"
                        />
                        <button
                            type="button"
                            class="px-4 py-2.5 sm:py-2 bg-indigo-600 text-white rounded-lg font-semibold hover:bg-indigo-500 transition active:scale-95 disabled:opacity-50 shrink-0"
                            :disabled="requestHash.length !== 32"
                            @click="requestPath"
                        >
                            Request
                        </button>
                    </div>
                </section>

                <!-- drop all via -->
                <section class="rounded-lg border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4 sm:p-6 space-y-4">
                    <h2 class="text-lg font-bold">Drop All Via</h2>
                    <p class="text-sm text-gray-500">
                        Remove all known paths routed through a specific transport instance.
                    </p>
                    <div class="flex flex-col sm:flex-row gap-2">
                        <input
                            v-model="dropViaHash"
                            type="text"
                            placeholder="Transport Instance Hash"
                            class="input-field flex-1 min-w-0 font-mono"
                        />
                        <button
                            type="button"
                            class="px-4 py-2.5 sm:py-2 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-500 transition active:scale-95 disabled:opacity-50 shrink-0"
                            :disabled="dropViaHash.length !== 32"
                            @click="dropAllVia"
                        >
                            Drop All
                        </button>
                    </div>
                </section>

                <!-- drop queues -->
                <section class="rounded-lg border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-4 sm:p-6 space-y-4">
                    <h2 class="text-lg font-bold">Drop Announce Queues</h2>
                    <p class="text-sm text-gray-500">
                        Clear all outbound announce packets currently queued on all interfaces.
                    </p>
                    <button
                        type="button"
                        class="w-full px-4 py-3 bg-zinc-800 text-white rounded-lg font-semibold hover:bg-zinc-700 transition active:scale-95"
                        @click="dropAnnounceQueues"
                    >
                        Purge All Queues
                    </button>
                </section>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToastUtils from "../../js/ToastUtils";
import DialogUtils from "../../js/DialogUtils";
import Utils from "../../js/Utils";

export default {
    name: "RNPathPage",
    components: {
        MaterialDesignIcon,
    },
    data() {
        return {
            tab: "table",
            isLoading: false,
            pathTable: [],
            rateTable: [],
            requestHash: "",
            dropViaHash: "",
            // Pagination & Filtering
            searchQuery: "",
            filterInterface: "",
            filterHops: null,
            currentPage: 1,
            itemsPerPage: 50,
            totalItems: 0,
            responsiveItems: 0,
            unresponsiveItems: 0,
            interfaces: [],
        };
    },
    computed: {
        totalPages() {
            return Math.ceil(this.totalItems / this.itemsPerPage);
        },
    },
    watch: {
        searchQuery() {
            this.currentPage = 1;
            this.refreshTable();
        },
        filterInterface() {
            this.currentPage = 1;
            this.refreshTable();
        },
        filterHops() {
            this.currentPage = 1;
            this.refreshTable();
        },
        currentPage() {
            this.refreshTable();
        },
    },
    mounted() {
        this.refreshAll();
    },
    methods: {
        async refreshAll() {
            this.isLoading = true;
            try {
                const [pathRes, rateRes, ifaceRes, discRes] = await Promise.all([
                    this.fetchPathTable(),
                    window.api.get("/api/v1/rnpath/rates"),
                    window.api.get("/api/v1/reticulum/interfaces"),
                    window.api.get("/api/v1/reticulum/discovered-interfaces").catch(() => ({ data: {} })),
                ]);
                this.pathTable = pathRes.table;
                this.totalItems = pathRes.total;
                this.responsiveItems = pathRes.responsive;
                this.unresponsiveItems = pathRes.unresponsive;
                this.rateTable = rateRes.data.rates;
                const nameSet = new Set(Object.keys(ifaceRes.data?.interfaces || {}));
                for (const row of discRes.data?.active || []) {
                    if (row?.name) {
                        nameSet.add(String(row.name));
                    }
                }
                for (const d of discRes.data?.interfaces || []) {
                    if (d && typeof d === "object" && d.name) {
                        nameSet.add(String(d.name));
                    }
                }
                this.interfaces = Array.from(nameSet).sort();
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("tools.rnpath.failed_fetch"));
            } finally {
                this.isLoading = false;
            }
        },
        async refreshTable() {
            this.isLoading = true;
            try {
                const res = await this.fetchPathTable();
                this.pathTable = res.table;
                this.totalItems = res.total;
                this.responsiveItems = res.responsive;
                this.unresponsiveItems = res.unresponsive;
            } catch (e) {
                console.error(e);
            } finally {
                this.isLoading = false;
            }
        },
        async fetchPathTable() {
            const params = {
                page: this.currentPage,
                limit: this.itemsPerPage,
                search: this.searchQuery || undefined,
                interface: this.filterInterface || undefined,
                hops: this.filterHops !== null ? this.filterHops : undefined,
            };
            const res = await window.api.get("/api/v1/rnpath/table", { params });
            return res.data;
        },
        getStateColor(state) {
            if (state === 2) return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300";
            if (state === 1) return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300";
            return "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400";
        },
        getStateText(state) {
            if (state === 2) return "RESPONSIVE";
            if (state === 1) return "UNRESPONSIVE";
            return "UNKNOWN";
        },
        async dropPath(hash) {
            if (!(await DialogUtils.confirm(`Are you sure you want to drop the path to ${hash}?`))) {
                return;
            }
            try {
                const res = await window.api.post("/api/v1/rnpath/drop", { destination_hash: hash });
                if (res.data.success) {
                    ToastUtils.success(this.$t("tools.rnpath.path_dropped"));
                    this.refreshAll();
                } else {
                    ToastUtils.error(this.$t("tools.rnpath.failed_drop"));
                }
            } catch {
                ToastUtils.error(this.$t("tools.rnpath.error_drop"));
            }
        },
        async requestPath() {
            try {
                await window.api.post("/api/v1/rnpath/request", { destination_hash: this.requestHash });
                ToastUtils.success(`Path requested for ${this.requestHash.substring(0, 8)}...`);
                this.requestHash = "";
                // Path requests take time, don't refresh immediately
            } catch {
                ToastUtils.error(this.$t("tools.rnpath.failed_request"));
            }
        },
        async dropAllVia() {
            if (!(await DialogUtils.confirm(`Drop ALL paths via ${this.dropViaHash}?`))) {
                return;
            }
            try {
                const res = await window.api.post("/api/v1/rnpath/drop-via", {
                    transport_instance_hash: this.dropViaHash,
                });
                if (res.data.success) {
                    ToastUtils.success(this.$t("tools.rnpath.paths_dropped"));
                    this.dropViaHash = "";
                    this.refreshAll();
                }
            } catch {
                ToastUtils.error(this.$t("tools.rnpath.failed_drop_paths"));
            }
        },
        async dropAnnounceQueues() {
            if (!(await DialogUtils.confirm(this.$t("tools.rnpath.purge_confirm")))) {
                return;
            }
            try {
                await window.api.post("/api/v1/rnpath/drop-queues");
                ToastUtils.success(this.$t("tools.rnpath.queues_purged"));
            } catch {
                ToastUtils.error(this.$t("tools.rnpath.failed_purge"));
            }
        },
        calculateRate(rate) {
            if (rate.timestamps.length === 0) return 0;
            const startTs = rate.timestamps[0];
            const span = Math.max(Date.now() / 1000 - startTs, 3600.0);
            const spanHours = span / 3600.0;
            return (rate.timestamps.length / spanHours).toFixed(2);
        },
        formatDate(ts) {
            return new Date(ts * 1000).toLocaleString();
        },
        formatTimeAgo(ts) {
            return Utils.formatSecondsAgo(Math.floor(Date.now() / 1000 - ts));
        },
    },
};
</script>

<style scoped>
.input-field {
    @apply bg-gray-50/90 dark:bg-zinc-800/80 border border-gray-200 dark:border-zinc-700 text-sm rounded-xl focus:ring-2 focus:ring-indigo-400 focus:border-indigo-400 dark:focus:ring-indigo-500 dark:focus:border-indigo-500 block w-full p-3 text-gray-900 dark:text-gray-100 transition;
}
</style>
