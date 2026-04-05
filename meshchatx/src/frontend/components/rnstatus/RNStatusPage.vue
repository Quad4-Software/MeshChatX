<template>
    <div
        class="flex flex-col flex-1 overflow-hidden min-w-0 bg-gradient-to-br from-slate-50 via-slate-100 to-white dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-900"
    >
        <div class="flex-1 overflow-y-auto w-full px-4 md:px-8 py-6">
            <div class="space-y-4 w-full max-w-6xl mx-auto">
                <div class="glass-card space-y-5 rounded-2xl border border-slate-200/70 p-5 dark:border-zinc-700/80">
                    <div class="space-y-2">
                        <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                            Network Diagnostics
                        </div>
                        <div class="text-2xl font-semibold text-gray-900 dark:text-white">
                            RNStatus - Network Status
                        </div>
                        <div class="text-sm text-gray-600 dark:text-gray-300">
                            View interface statistics and network status information.
                        </div>
                    </div>

                    <div class="flex flex-wrap items-center gap-2">
                        <button
                            type="button"
                            class="primary-chip inline-flex items-center gap-2 px-4 py-2 text-sm"
                            :disabled="isLoading"
                            @click="refreshStatus"
                        >
                            <MaterialDesignIcon
                                icon-name="refresh"
                                class="h-4 w-4 shrink-0"
                                :class="{ 'animate-spin-reverse': isLoading }"
                            />
                            Refresh
                        </button>
                        <label
                            class="secondary-chip inline-flex cursor-pointer items-center gap-2 px-4 py-2 text-sm"
                        >
                            <input v-model="includeLinkStats" type="checkbox" class="rounded" />
                            <span>Include Link Stats</span>
                        </label>
                        <div class="flex min-w-0 flex-wrap items-center gap-2">
                            <label class="shrink-0 text-sm text-gray-700 dark:text-gray-300">Sort by:</label>
                            <select v-model="sorting" class="input-field min-w-[10rem] text-sm">
                                <option value="">None</option>
                                <option value="bitrate">Bitrate</option>
                                <option value="rx">RX Bytes</option>
                                <option value="tx">TX Bytes</option>
                                <option value="traffic">Total Traffic</option>
                                <option value="announces">Announces</option>
                            </select>
                        </div>
                    </div>

                    <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
                        <div
                            v-if="linkCount !== null"
                            class="rounded-xl border border-blue-200/80 bg-blue-50/90 p-4 text-blue-800 dark:border-blue-800/50 dark:bg-blue-950/30 dark:text-blue-200"
                        >
                            <div class="text-sm font-semibold">
                                Active Links: {{ formatInt(linkCount) }}
                            </div>
                        </div>

                        <div
                            v-if="blackholeEnabled !== null"
                            class="rounded-xl border border-purple-200/80 bg-purple-50/90 p-4 text-purple-900 dark:border-purple-800/50 dark:bg-purple-950/30 dark:text-purple-100"
                        >
                            <div class="flex flex-wrap items-center justify-between gap-2 font-semibold">
                                <span>Blackhole: {{ blackholeEnabled ? "Publishing" : "Active" }}</span>
                                <span class="text-sm font-normal opacity-90">
                                    {{ formatInt(blackholeCount) }} Identities
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                <div
                    v-if="blackholeSources.length > 0"
                    class="glass-card space-y-3 rounded-2xl border border-slate-200/70 p-5 dark:border-zinc-700/80"
                >
                    <div class="font-semibold text-lg text-gray-900 dark:text-white">Blackhole Sources</div>
                    <div class="grid gap-2">
                        <div
                            v-for="source in blackholeSources"
                            :key="source"
                            class="text-sm font-mono bg-gray-50 dark:bg-gray-800 p-2 rounded truncate"
                        >
                            {{ source }}
                        </div>
                    </div>
                </div>

                <div
                    v-if="interfaces.length === 0 && !isLoading"
                    class="glass-card p-8 text-center text-gray-500 dark:text-gray-400"
                >
                    No interfaces found. Click refresh to load status.
                </div>

                <div
                    v-for="iface in interfaces"
                    :key="iface.name"
                    class="glass-card overflow-hidden rounded-2xl border border-slate-200/70 dark:border-zinc-700/80"
                >
                    <div
                        class="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 bg-slate-50/60 px-4 py-4 dark:border-zinc-800/80 dark:bg-zinc-900/40 sm:px-5"
                    >
                        <div class="min-w-0 flex-1 space-y-2">
                            <div class="flex flex-wrap items-center gap-2">
                                <h3
                                    class="break-words text-base font-semibold leading-snug text-gray-900 dark:text-white sm:text-lg"
                                >
                                    {{ iface.name }}
                                </h3>
                                <span
                                    v-if="iface.discovered"
                                    class="inline-flex shrink-0 items-center rounded-md bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-900 dark:bg-amber-900/45 dark:text-amber-100"
                                >
                                    Discovered
                                </span>
                            </div>
                        </div>
                        <span
                            :class="[
                                iface.status === 'Up'
                                    ? 'bg-green-100 text-green-800 dark:bg-green-900/45 dark:text-green-100'
                                    : 'bg-red-100 text-red-800 dark:bg-red-900/45 dark:text-red-100',
                                'shrink-0 rounded-full px-3 py-1 text-xs font-semibold',
                            ]"
                        >
                            {{ iface.status }}
                        </span>
                    </div>

                    <div class="grid gap-x-6 gap-y-4 p-4 text-sm sm:p-5 md:grid-cols-2 lg:grid-cols-3">
                        <div v-if="iface.mode">
                            <div class="text-gray-500 dark:text-gray-400">Mode</div>
                            <div class="font-semibold text-gray-900 dark:text-white">{{ iface.mode }}</div>
                        </div>
                        <div v-if="iface.bitrate">
                            <div class="text-gray-500 dark:text-gray-400">Bitrate</div>
                            <div class="font-semibold text-gray-900 dark:text-white">{{ iface.bitrate }}</div>
                        </div>
                        <div v-if="iface.rx_bytes_str">
                            <div class="text-gray-500 dark:text-gray-400">RX Bytes</div>
                            <div class="font-semibold text-gray-900 dark:text-white">{{ iface.rx_bytes_str }}</div>
                        </div>
                        <div v-if="iface.tx_bytes_str">
                            <div class="text-gray-500 dark:text-gray-400">TX Bytes</div>
                            <div class="font-semibold text-gray-900 dark:text-white">{{ iface.tx_bytes_str }}</div>
                        </div>
                        <div v-if="iface.rx_packets !== undefined">
                            <div class="text-gray-500 dark:text-gray-400">RX Packets</div>
                            <div class="font-semibold tabular-nums text-gray-900 dark:text-white">
                                {{ iface.rx_packets }}
                            </div>
                        </div>
                        <div v-if="iface.tx_packets !== undefined">
                            <div class="text-gray-500 dark:text-gray-400">TX Packets</div>
                            <div class="font-semibold tabular-nums text-gray-900 dark:text-white">
                                {{ iface.tx_packets }}
                            </div>
                        </div>
                        <div v-if="iface.clients !== undefined">
                            <div class="text-gray-500 dark:text-gray-400">Clients</div>
                            <div class="font-semibold text-gray-900 dark:text-white">{{ formatInt(iface.clients) }}</div>
                        </div>
                        <div v-if="iface.peers !== undefined">
                            <div class="text-gray-500 dark:text-gray-400">Peers</div>
                            <div class="font-semibold text-gray-900 dark:text-white">
                                {{ formatInt(iface.peers) }} reachable
                            </div>
                        </div>
                        <div v-if="iface.noise_floor">
                            <div class="text-gray-500 dark:text-gray-400">Noise Floor</div>
                            <div class="font-semibold text-gray-900 dark:text-white">{{ iface.noise_floor }}</div>
                        </div>
                        <div v-if="iface.interference">
                            <div class="text-gray-500 dark:text-gray-400">Interference</div>
                            <div class="font-semibold text-gray-900 dark:text-white">{{ iface.interference }}</div>
                        </div>
                        <div v-if="iface.cpu_load">
                            <div class="text-gray-500 dark:text-gray-400">CPU Load</div>
                            <div class="font-semibold text-gray-900 dark:text-white">{{ iface.cpu_load }}</div>
                        </div>
                        <div v-if="iface.cpu_temp">
                            <div class="text-gray-500 dark:text-gray-400">CPU Temp</div>
                            <div class="font-semibold text-gray-900 dark:text-white">{{ iface.cpu_temp }}</div>
                        </div>
                        <div v-if="iface.mem_load">
                            <div class="text-gray-500 dark:text-gray-400">Memory Load</div>
                            <div class="font-semibold text-gray-900 dark:text-white">{{ iface.mem_load }}</div>
                        </div>
                        <div v-if="iface.battery_percent !== undefined">
                            <div class="text-gray-500 dark:text-gray-400">Battery</div>
                            <div class="font-semibold text-gray-900 dark:text-white">
                                {{ formatInt(iface.battery_percent) }}%<span v-if="iface.battery_state">
                                    ({{ iface.battery_state }})</span
                                >
                            </div>
                        </div>
                        <div v-if="iface.network_name">
                            <div class="text-gray-500 dark:text-gray-400">Network</div>
                            <div class="font-semibold text-gray-900 dark:text-white">{{ iface.network_name }}</div>
                        </div>
                        <div v-if="iface.incoming_announce_frequency !== undefined">
                            <div class="text-gray-500 dark:text-gray-400">Incoming Announces</div>
                            <div class="font-semibold tabular-nums text-gray-900 dark:text-white">
                                {{ iface.incoming_announce_frequency }}/s
                            </div>
                        </div>
                        <div v-if="iface.outgoing_announce_frequency !== undefined">
                            <div class="text-gray-500 dark:text-gray-400">Outgoing Announces</div>
                            <div class="font-semibold tabular-nums text-gray-900 dark:text-white">
                                {{ iface.outgoing_announce_frequency }}/s
                            </div>
                        </div>
                        <div v-if="iface.airtime">
                            <div class="text-gray-500 dark:text-gray-400">Airtime</div>
                            <div class="font-semibold text-gray-900 dark:text-white">
                                {{ iface.airtime.short }}% (15s), {{ iface.airtime.long }}% (1h)
                            </div>
                        </div>
                        <div v-if="iface.channel_load">
                            <div class="text-gray-500 dark:text-gray-400">Channel Load</div>
                            <div class="font-semibold text-gray-900 dark:text-white">
                                {{ iface.channel_load.short }}% (15s), {{ iface.channel_load.long }}% (1h)
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

export default {
    name: "RNStatusPage",
    components: {
        MaterialDesignIcon,
    },
    data() {
        return {
            isLoading: false,
            interfaces: [],
            linkCount: null,
            includeLinkStats: false,
            sorting: "",
            blackholeEnabled: null,
            blackholeSources: [],
            blackholeCount: 0,
        };
    },
    watch: {
        sorting() {
            this.refreshStatus();
        },
        includeLinkStats() {
            this.refreshStatus();
        },
    },
    mounted() {
        this.refreshStatus();
    },
    methods: {
        formatInt(value) {
            if (value === null || value === undefined) {
                return "";
            }
            const n = Number(value);
            if (Number.isNaN(n)) {
                return String(value);
            }
            return n.toLocaleString();
        },
        async refreshStatus() {
            this.isLoading = true;
            try {
                const params = {
                    include_link_stats: this.includeLinkStats,
                };
                if (this.sorting) {
                    params.sorting = this.sorting;
                }
                const response = await window.api.get("/api/v1/rnstatus", { params });
                this.interfaces = response.data.interfaces || [];
                this.linkCount = response.data.link_count;
                this.blackholeEnabled = response.data.blackhole_enabled;
                this.blackholeSources = response.data.blackhole_sources || [];
                this.blackholeCount = response.data.blackhole_count || 0;
            } catch (e) {
                console.error(e);
            } finally {
                this.isLoading = false;
            }
        },
    },
};
</script>
