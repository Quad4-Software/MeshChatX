<template>
    <div
        class="flex flex-col flex-1 overflow-hidden min-w-0 bg-gradient-to-br from-slate-50 via-slate-100 to-white dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-900"
    >
        <div class="flex-1 overflow-y-auto w-full px-4 md:px-8 py-6">
            <div class="space-y-4 w-full max-w-6xl mx-auto">
                <div class="glass-card space-y-5">
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

                    <div class="flex flex-wrap gap-2">
                        <button
                            type="button"
                            class="primary-chip px-4 py-2 text-sm"
                            :disabled="isLoading"
                            @click="refreshStatus"
                        >
                            <MaterialDesignIcon
                                icon-name="refresh"
                                class="w-4 h-4"
                                :class="{ 'animate-spin-reverse': isLoading }"
                            />
                            Refresh
                        </button>
                        <label class="flex items-center gap-2 cursor-pointer secondary-chip px-4 py-2 text-sm">
                            <input v-model="includeLinkStats" type="checkbox" class="rounded" />
                            <span>Include Link Stats</span>
                        </label>
                        <div class="flex items-center gap-2">
                            <label class="text-sm text-gray-700 dark:text-gray-300">Sort by:</label>
                            <select v-model="sorting" class="input-field text-sm">
                                <option value="">None</option>
                                <option value="bitrate">Bitrate</option>
                                <option value="rx">RX Bytes</option>
                                <option value="tx">TX Bytes</option>
                                <option value="traffic">Total Traffic</option>
                                <option value="announces">Announces</option>
                            </select>
                        </div>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div
                            v-if="linkCount !== null"
                            class="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300"
                        >
                            <div class="font-semibold">Active Links: {{ linkCount }}</div>
                        </div>

                        <div
                            v-if="blackholeEnabled !== null"
                            class="p-3 rounded-lg bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300"
                        >
                            <div class="font-semibold flex justify-between items-center">
                                <span>Blackhole: {{ blackholeEnabled ? "Publishing" : "Active" }}</span>
                                <span class="text-sm opacity-80"> {{ blackholeCount }} Identities </span>
                            </div>
                        </div>
                    </div>
                </div>

                <div v-if="blackholeSources.length > 0" class="glass-card space-y-3">
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

                <div v-for="iface in interfaces" :key="iface.name" class="glass-card space-y-3">
                    <div class="flex items-center justify-between">
                        <div class="font-semibold text-lg text-gray-900 dark:text-white">{{ iface.name }}</div>
                        <span
                            :class="[
                                iface.status === 'Up'
                                    ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-200'
                                    : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-200',
                                'rounded-full px-3 py-1 text-xs font-semibold',
                            ]"
                        >
                            {{ iface.status }}
                        </span>
                    </div>

                    <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
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
                            <div class="font-semibold text-gray-900 dark:text-white">{{ iface.rx_packets }}</div>
                        </div>
                        <div v-if="iface.tx_packets !== undefined">
                            <div class="text-gray-500 dark:text-gray-400">TX Packets</div>
                            <div class="font-semibold text-gray-900 dark:text-white">{{ iface.tx_packets }}</div>
                        </div>
                        <div v-if="iface.clients !== undefined">
                            <div class="text-gray-500 dark:text-gray-400">Clients</div>
                            <div class="font-semibold text-gray-900 dark:text-white">{{ iface.clients }}</div>
                        </div>
                        <div v-if="iface.peers !== undefined">
                            <div class="text-gray-500 dark:text-gray-400">Peers</div>
                            <div class="font-semibold text-gray-900 dark:text-white">{{ iface.peers }} reachable</div>
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
                                {{ iface.battery_percent }}%<span v-if="iface.battery_state">
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
                            <div class="font-semibold text-gray-900 dark:text-white">
                                {{ iface.incoming_announce_frequency }}/s
                            </div>
                        </div>
                        <div v-if="iface.outgoing_announce_frequency !== undefined">
                            <div class="text-gray-500 dark:text-gray-400">Outgoing Announces</div>
                            <div class="font-semibold text-gray-900 dark:text-white">
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
        async refreshStatus() {
            this.isLoading = true;
            try {
                const params = {
                    include_link_stats: this.includeLinkStats,
                };
                if (this.sorting) {
                    params.sorting = this.sorting;
                }
                const response = await window.axios.get("/api/v1/rnstatus", { params });
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
