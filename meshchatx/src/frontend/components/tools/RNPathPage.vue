<template>
    <div class="flex flex-col flex-1 h-full overflow-hidden bg-slate-50 dark:bg-zinc-950">
        <!-- header -->
        <div
            class="flex items-center px-4 py-4 bg-white dark:bg-zinc-900 border-b border-gray-200 dark:border-zinc-800 shadow-sm"
        >
            <div class="flex items-center gap-3">
                <div class="p-2 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg">
                    <MaterialDesignIcon icon-name="route" class="size-6 text-indigo-600 dark:text-indigo-400" />
                </div>
                <div>
                    <h1 class="text-xl font-bold text-gray-900 dark:text-white">RNPath</h1>
                    <p class="text-sm text-gray-500 dark:text-gray-400">Reticulum Path Management Utility</p>
                </div>
            </div>

            <div class="ml-auto flex items-center gap-2">
                <button
                    class="p-2 text-gray-500 hover:text-indigo-500 dark:text-gray-400 dark:hover:text-indigo-400 transition-colors"
                    title="Refresh"
                    @click="refreshAll"
                >
                    <MaterialDesignIcon icon-name="refresh" class="size-6" :class="{ 'animate-spin': isLoading }" />
                </button>
            </div>
        </div>

        <div class="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
            <!-- tabs -->
            <div class="flex border-b border-gray-200 dark:border-zinc-800">
                <button
                    v-for="t in ['table', 'rates', 'actions']"
                    :key="t"
                    class="px-6 py-3 text-sm font-semibold transition-colors border-b-2 -mb-px"
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

            <!-- path table -->
            <div v-if="tab === 'table'" class="space-y-4">
                <div v-if="pathTable.length === 0" class="glass-card p-12 text-center text-gray-500">
                    No paths currently known.
                </div>
                <div v-else class="grid gap-4">
                    <div
                        v-for="path in pathTable"
                        :key="path.hash"
                        class="glass-card p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                    >
                        <div class="min-w-0">
                            <div class="flex items-center gap-2 mb-1">
                                <span class="font-mono text-sm font-bold text-indigo-600 dark:text-indigo-400 truncate">
                                    {{ path.hash }}
                                </span>
                                <span
                                    class="px-2 py-0.5 text-[10px] font-bold bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded uppercase tracking-wider"
                                >
                                    {{ path.hops }} {{ path.hops === 1 ? "hop" : "hops" }}
                                </span>
                            </div>
                            <div class="text-xs text-gray-500 dark:text-gray-400 font-mono truncate">
                                via {{ path.via }} on {{ path.interface }}
                            </div>
                            <div class="text-[10px] text-gray-400 mt-1">Expires: {{ formatDate(path.expires) }}</div>
                        </div>
                        <button
                            class="px-3 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20 rounded-lg transition-colors border border-red-200 dark:border-red-900/30"
                            @click="dropPath(path.hash)"
                        >
                            Drop Path
                        </button>
                    </div>
                </div>
            </div>

            <!-- announce rates -->
            <div v-if="tab === 'rates'" class="space-y-4">
                <div v-if="rateTable.length === 0" class="glass-card p-12 text-center text-gray-500">
                    No announce rate data available.
                </div>
                <div v-else class="grid gap-4">
                    <div v-for="rate in rateTable" :key="rate.hash" class="glass-card p-4">
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
                <section class="glass-card p-6 space-y-4">
                    <h2 class="text-lg font-bold">Request Path</h2>
                    <p class="text-sm text-gray-500">Broadcast a path request for a destination hash.</p>
                    <div class="flex gap-2">
                        <input
                            v-model="requestHash"
                            type="text"
                            placeholder="Destination Hash (32 hex chars)"
                            class="input-field flex-1 font-mono"
                        />
                        <button
                            class="px-4 py-2 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-500 transition shadow-lg shadow-indigo-500/20 active:scale-95 disabled:opacity-50"
                            :disabled="requestHash.length !== 32"
                            @click="requestPath"
                        >
                            Request
                        </button>
                    </div>
                </section>

                <!-- drop all via -->
                <section class="glass-card p-6 space-y-4">
                    <h2 class="text-lg font-bold">Drop All Via</h2>
                    <p class="text-sm text-gray-500">
                        Remove all known paths routed through a specific transport instance.
                    </p>
                    <div class="flex gap-2">
                        <input
                            v-model="dropViaHash"
                            type="text"
                            placeholder="Transport Instance Hash"
                            class="input-field flex-1 font-mono"
                        />
                        <button
                            class="px-4 py-2 bg-red-600 text-white rounded-xl font-semibold hover:bg-red-500 transition shadow-lg shadow-red-500/20 active:scale-95 disabled:opacity-50"
                            :disabled="dropViaHash.length !== 32"
                            @click="dropAllVia"
                        >
                            Drop All
                        </button>
                    </div>
                </section>

                <!-- drop queues -->
                <section class="glass-card p-6 space-y-4">
                    <h2 class="text-lg font-bold">Drop Announce Queues</h2>
                    <p class="text-sm text-gray-500">
                        Clear all outbound announce packets currently queued on all interfaces.
                    </p>
                    <button
                        class="w-full px-4 py-3 bg-zinc-800 text-white rounded-xl font-semibold hover:bg-zinc-700 transition active:scale-95"
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
        };
    },
    mounted() {
        this.refreshAll();
    },
    methods: {
        async refreshAll() {
            this.isLoading = true;
            try {
                const [pathRes, rateRes] = await Promise.all([
                    window.axios.get("/api/v1/rnpath/table"),
                    window.axios.get("/api/v1/rnpath/rates"),
                ]);
                this.pathTable = pathRes.data.table;
                this.rateTable = rateRes.data.rates;
            } catch (e) {
                console.error(e);
                ToastUtils.error("Failed to fetch path data");
            } finally {
                this.isLoading = false;
            }
        },
        async dropPath(hash) {
            if (!(await DialogUtils.confirm(`Are you sure you want to drop the path to ${hash}?`))) {
                return;
            }
            try {
                const res = await window.axios.post("/api/v1/rnpath/drop", { destination_hash: hash });
                if (res.data.success) {
                    ToastUtils.success("Path dropped");
                    this.refreshAll();
                } else {
                    ToastUtils.error("Could not drop path");
                }
            } catch {
                ToastUtils.error("Error dropping path");
            }
        },
        async requestPath() {
            try {
                await window.axios.post("/api/v1/rnpath/request", { destination_hash: this.requestHash });
                ToastUtils.success(`Path requested for ${this.requestHash.substring(0, 8)}...`);
                this.requestHash = "";
                // Path requests take time, don't refresh immediately
            } catch {
                ToastUtils.error("Failed to request path");
            }
        },
        async dropAllVia() {
            if (!(await DialogUtils.confirm(`Drop ALL paths via ${this.dropViaHash}?`))) {
                return;
            }
            try {
                const res = await window.axios.post("/api/v1/rnpath/drop-via", {
                    transport_instance_hash: this.dropViaHash,
                });
                if (res.data.success) {
                    ToastUtils.success("Paths dropped");
                    this.dropViaHash = "";
                    this.refreshAll();
                }
            } catch {
                ToastUtils.error("Failed to drop paths");
            }
        },
        async dropAnnounceQueues() {
            if (!(await DialogUtils.confirm("Purge all announce queues? This cannot be undone."))) {
                return;
            }
            try {
                await window.axios.post("/api/v1/rnpath/drop-queues");
                ToastUtils.success("Announce queues purged");
            } catch {
                ToastUtils.error("Failed to purge queues");
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
.glass-card {
    @apply bg-white/90 dark:bg-zinc-900/80 backdrop-blur border border-gray-200 dark:border-zinc-800 rounded-2xl shadow-lg;
}
.input-field {
    @apply bg-gray-50/90 dark:bg-zinc-800/80 border border-gray-200 dark:border-zinc-700 text-sm rounded-xl focus:ring-2 focus:ring-indigo-400 focus:border-indigo-400 dark:focus:ring-indigo-500 dark:focus:border-indigo-500 block w-full p-3 text-gray-900 dark:text-gray-100 transition;
}
</style>
