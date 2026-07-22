<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-slate-50 dark:bg-zinc-950">
        <ToolsPageHeader
            icon="chart-line"
            :title="$t('tools.rnstatus.title')"
            :description="$t('tools.rnstatus.description')"
            :eyebrow="$t('rnprobe.network_diagnostics')"
            accent="orange"
        >
            <template #actions>
                <button
                    type="button"
                    class="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-orange-600 text-white text-sm font-medium hover:bg-orange-700 disabled:opacity-50 disabled:pointer-events-none"
                    :disabled="isLoading || reloadingRns"
                    @click="refreshStatus"
                >
                    <MaterialDesignIcon
                        icon-name="refresh"
                        class="h-4 w-4 shrink-0"
                        :class="{ 'animate-spin-reverse': isLoading || reloadingRns }"
                    />
                    <span class="hidden sm:inline">{{
                        reloadingRns ? $t("rnstatus.reloading") : $t("rnstatus.refresh")
                    }}</span>
                </button>
            </template>
        </ToolsPageHeader>
        <div class="flex-1 overflow-y-auto overflow-x-hidden w-full px-3 sm:px-5 md:px-5 lg:px-8 py-3 sm:py-4 min-w-0">
            <div class="space-y-0 w-full max-w-6xl xl:max-w-7xl mx-auto min-w-0">
                <div class="w-full border-b border-gray-200/60 dark:border-zinc-800/60 py-4 sm:py-6 space-y-3">
                    <div class="flex flex-wrap items-center gap-3">
                        <label
                            class="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm text-gray-800 dark:text-zinc-200"
                        >
                            <input
                                v-model="includeLinkStats"
                                type="checkbox"
                                class="rounded-sm"
                                :disabled="reloadingRns"
                            />
                            <span>{{ $t("rnstatus.include_link_stats") }}</span>
                        </label>
                        <div class="flex min-w-0 flex-wrap items-center gap-2">
                            <label class="shrink-0 text-sm text-gray-700 dark:text-gray-300">{{
                                $t("rnstatus.sort_by")
                            }}</label>
                            <select v-model="sorting" class="input-field min-w-40 text-sm" :disabled="reloadingRns">
                                <option value="">{{ $t("rnstatus.none") }}</option>
                                <option value="bitrate">{{ $t("rnstatus.bitrate") }}</option>
                                <option value="rx">{{ $t("rnstatus.rx_bytes") }}</option>
                                <option value="tx">{{ $t("rnstatus.tx_bytes") }}</option>
                                <option value="traffic">{{ $t("rnstatus.total_traffic") }}</option>
                                <option value="announces">{{ $t("rnstatus.announces") }}</option>
                            </select>
                        </div>
                    </div>
                </div>

                <div class="w-full border-b border-gray-200/60 dark:border-zinc-800/60 py-4 sm:py-6 space-y-3">
                    <h2 class="text-sm font-semibold text-gray-900 dark:text-white">
                        {{ $t("rnstatus.remote_query") }}
                    </h2>
                    <p class="text-xs text-gray-500 dark:text-zinc-500">
                        {{ $t("rnstatus.remote_query_hint") }}
                    </p>
                    <div class="grid gap-3 lg:grid-cols-2">
                        <label class="block space-y-1">
                            <span class="text-xs font-medium text-gray-700 dark:text-zinc-300">{{
                                $t("rnstatus.remote_transport_hash")
                            }}</span>
                            <input
                                v-model="remoteHash"
                                type="text"
                                class="input-field font-mono text-xs"
                                :placeholder="$t('rnstatus.remote_transport_placeholder')"
                                :disabled="reloadingRns"
                            />
                        </label>
                        <label class="block space-y-1">
                            <span class="text-xs font-medium text-gray-700 dark:text-zinc-300">{{
                                $t("rnstatus.remote_timeout")
                            }}</span>
                            <input
                                v-model.number="remoteTimeout"
                                type="number"
                                min="1"
                                step="1"
                                class="input-field text-sm"
                                :disabled="reloadingRns"
                            />
                        </label>
                    </div>
                    <ManagementIdentityPicker v-model="identityPath" :disabled="reloadingRns" default-name="mgmt" />
                    <div v-if="activeRemoteHash" class="flex flex-wrap items-center gap-2 text-xs">
                        <span class="font-mono text-amber-700 dark:text-amber-300">{{
                            $t("rnstatus.remote_active", { hash: activeRemoteHash })
                        }}</span>
                        <button
                            type="button"
                            class="inline-flex items-center px-2 py-1 rounded-lg border border-gray-300 dark:border-zinc-600 bg-white dark:bg-zinc-900 text-xs font-medium text-gray-800 dark:text-zinc-200 hover:bg-gray-50 dark:hover:bg-zinc-800"
                            @click="clearRemote"
                        >
                            {{ $t("rnstatus.use_local") }}
                        </button>
                    </div>
                </div>

                <div
                    v-if="linkCount !== null || blackholeEnabled !== null"
                    class="w-full border-b border-gray-200/60 dark:border-zinc-800/60 py-4 sm:py-6"
                >
                    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                        <div
                            v-if="linkCount !== null"
                            class="text-sm font-semibold text-gray-900 dark:text-white tabular-nums"
                        >
                            {{ $t("rnstatus.active_links", { count: formatInt(linkCount) }) }}
                        </div>
                        <div v-if="blackholeEnabled !== null" class="space-y-0.5">
                            <div class="text-sm font-semibold text-gray-900 dark:text-white">
                                {{
                                    $t("rnstatus.blackhole_label", {
                                        state: blackholeEnabled
                                            ? $t("rnstatus.blackhole_publishing")
                                            : $t("rnstatus.blackhole_inactive"),
                                    })
                                }}
                            </div>
                            <div class="text-xs text-gray-500 dark:text-zinc-500 tabular-nums">
                                {{ formatInt(blackholeCount) }} Identities
                            </div>
                        </div>
                    </div>
                </div>

                <div
                    v-if="blackholeSources.length > 0"
                    class="w-full border-b border-gray-200/60 dark:border-zinc-800/60 py-4 sm:py-6 space-y-3"
                >
                    <h2 class="text-sm font-semibold text-gray-900 dark:text-white">Blackhole Sources</h2>
                    <div class="divide-y divide-gray-100 dark:divide-zinc-800/50">
                        <div
                            v-for="source in blackholeSources"
                            :key="source"
                            class="py-2 text-sm font-mono text-gray-800 dark:text-zinc-200 truncate"
                        >
                            {{ source }}
                        </div>
                    </div>
                </div>

                <div
                    v-if="interfaces.length === 0 && !isLoading && !reloadingRns"
                    class="w-full py-8 sm:py-12 text-center text-sm text-gray-500 dark:text-gray-400"
                >
                    {{ $t("rnstatus.no_interfaces_found") }}
                </div>

                <div v-else class="w-full divide-y divide-gray-200/60 dark:divide-zinc-800/60">
                    <div v-for="iface in interfaces" :key="iface.name" class="py-4 sm:py-6 space-y-4">
                        <div class="flex flex-wrap items-start justify-between gap-3">
                            <div class="min-w-0 flex-1 space-y-1">
                                <div class="flex flex-wrap items-center gap-2">
                                    <h3
                                        class="wrap-break-word text-base font-semibold leading-snug text-gray-900 dark:text-white"
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

                        <div class="grid gap-x-6 gap-y-3 text-sm md:grid-cols-2 lg:grid-cols-3">
                            <div v-if="iface.mode">
                                <div class="text-xs text-gray-500 dark:text-gray-400">{{ $t("rnstatus.mode") }}</div>
                                <div class="font-semibold text-gray-900 dark:text-white">{{ iface.mode }}</div>
                            </div>
                            <div v-if="iface.bitrate">
                                <div class="text-xs text-gray-500 dark:text-gray-400">{{ $t("rnstatus.bitrate") }}</div>
                                <div class="font-semibold text-gray-900 dark:text-white">{{ iface.bitrate }}</div>
                            </div>
                            <div v-if="iface.rx_bytes_str">
                                <div class="text-xs text-gray-500 dark:text-gray-400">
                                    {{ $t("rnstatus.rx_bytes") }}
                                </div>
                                <div class="font-semibold text-gray-900 dark:text-white">{{ iface.rx_bytes_str }}</div>
                            </div>
                            <div v-if="iface.tx_bytes_str">
                                <div class="text-xs text-gray-500 dark:text-gray-400">
                                    {{ $t("rnstatus.tx_bytes") }}
                                </div>
                                <div class="font-semibold text-gray-900 dark:text-white">{{ iface.tx_bytes_str }}</div>
                            </div>
                            <div v-if="iface.rx_packets !== undefined">
                                <div class="text-xs text-gray-500 dark:text-gray-400">
                                    {{ $t("rnstatus.rx_packets") }}
                                </div>
                                <div class="font-semibold tabular-nums text-gray-900 dark:text-white">
                                    {{ iface.rx_packets }}
                                </div>
                            </div>
                            <div v-if="iface.tx_packets !== undefined">
                                <div class="text-xs text-gray-500 dark:text-gray-400">
                                    {{ $t("rnstatus.tx_packets") }}
                                </div>
                                <div class="font-semibold tabular-nums text-gray-900 dark:text-white">
                                    {{ iface.tx_packets }}
                                </div>
                            </div>
                            <div v-if="iface.clients !== undefined">
                                <div class="text-xs text-gray-500 dark:text-gray-400">{{ $t("rnstatus.clients") }}</div>
                                <div class="font-semibold text-gray-900 dark:text-white">
                                    {{ formatInt(iface.clients) }}
                                </div>
                            </div>
                            <div v-if="iface.peers !== undefined">
                                <div class="text-xs text-gray-500 dark:text-gray-400">Peers</div>
                                <div class="font-semibold text-gray-900 dark:text-white">
                                    {{ formatInt(iface.peers) }} {{ $t("rnstatus.peers_reachable") }}
                                </div>
                            </div>
                            <div v-if="iface.noise_floor">
                                <div class="text-xs text-gray-500 dark:text-gray-400">
                                    {{ $t("rnstatus.noise_floor") }}
                                </div>
                                <div class="font-semibold text-gray-900 dark:text-white">{{ iface.noise_floor }}</div>
                            </div>
                            <div v-if="iface.interference">
                                <div class="text-xs text-gray-500 dark:text-gray-400">
                                    {{ $t("rnstatus.interference") }}
                                </div>
                                <div class="font-semibold text-gray-900 dark:text-white">{{ iface.interference }}</div>
                            </div>
                            <div v-if="iface.cpu_load">
                                <div class="text-xs text-gray-500 dark:text-gray-400">
                                    {{ $t("rnstatus.cpu_load") }}
                                </div>
                                <div class="font-semibold text-gray-900 dark:text-white">{{ iface.cpu_load }}</div>
                            </div>
                            <div v-if="iface.cpu_temp">
                                <div class="text-xs text-gray-500 dark:text-gray-400">
                                    {{ $t("rnstatus.cpu_temp") }}
                                </div>
                                <div class="font-semibold text-gray-900 dark:text-white">{{ iface.cpu_temp }}</div>
                            </div>
                            <div v-if="iface.mem_load">
                                <div class="text-xs text-gray-500 dark:text-gray-400">
                                    {{ $t("rnstatus.memory_load") }}
                                </div>
                                <div class="font-semibold text-gray-900 dark:text-white">{{ iface.mem_load }}</div>
                            </div>
                            <div v-if="iface.battery_percent !== undefined">
                                <div class="text-xs text-gray-500 dark:text-gray-400">{{ $t("rnstatus.battery") }}</div>
                                <div class="font-semibold text-gray-900 dark:text-white">
                                    {{ formatInt(iface.battery_percent) }}%<span v-if="iface.battery_state">
                                        ({{ iface.battery_state }})</span
                                    >
                                </div>
                            </div>
                            <div v-if="iface.network_name">
                                <div class="text-xs text-gray-500 dark:text-gray-400">{{ $t("rnstatus.network") }}</div>
                                <div class="font-semibold text-gray-900 dark:text-white">{{ iface.network_name }}</div>
                            </div>
                            <div v-if="iface.incoming_announce_frequency !== undefined">
                                <div class="text-xs text-gray-500 dark:text-gray-400">
                                    {{ $t("rnstatus.incoming_announces") }}
                                </div>
                                <div class="font-semibold tabular-nums text-gray-900 dark:text-white">
                                    {{ iface.incoming_announce_frequency }}/s
                                </div>
                            </div>
                            <div v-if="iface.outgoing_announce_frequency !== undefined">
                                <div class="text-xs text-gray-500 dark:text-gray-400">
                                    {{ $t("rnstatus.outgoing_announces") }}
                                </div>
                                <div class="font-semibold tabular-nums text-gray-900 dark:text-white">
                                    {{ iface.outgoing_announce_frequency }}/s
                                </div>
                            </div>
                            <div v-if="iface.airtime">
                                <div class="text-xs text-gray-500 dark:text-gray-400">{{ $t("rnstatus.airtime") }}</div>
                                <div class="font-semibold text-gray-900 dark:text-white">
                                    {{ iface.airtime.short }}% (15s), {{ iface.airtime.long }}% (1h)
                                </div>
                            </div>
                            <div v-if="iface.channel_load">
                                <div class="text-xs text-gray-500 dark:text-gray-400">
                                    {{ $t("rnstatus.channel_load") }}
                                </div>
                                <div class="font-semibold text-gray-900 dark:text-white">
                                    {{ iface.channel_load.short }}% (15s), {{ iface.channel_load.long }}% (1h)
                                </div>
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
import ToolsPageHeader from "../tools/ToolsPageHeader.vue";
import ManagementIdentityPicker from "../tools/ManagementIdentityPicker.vue";
import ToastUtils from "../../js/ToastUtils";
import WebSocketConnection from "../../js/WebSocketConnection";

export default {
    name: "RNStatusPage",
    components: {
        MaterialDesignIcon,
        ToolsPageHeader,
        ManagementIdentityPicker,
    },
    data() {
        return {
            isLoading: false,
            reloadingRns: false,
            interfaces: [],
            linkCount: null,
            includeLinkStats: false,
            sorting: "",
            blackholeEnabled: null,
            blackholeSources: [],
            blackholeCount: 0,
            remoteHash: "",
            identityPath: "",
            remoteTimeout: 15,
            activeRemoteHash: "",
        };
    },
    watch: {
        sorting() {
            if (!this.reloadingRns) {
                this.refreshStatus();
            }
        },
        includeLinkStats() {
            if (!this.reloadingRns) {
                this.refreshStatus();
            }
        },
    },
    mounted() {
        WebSocketConnection.on("message", this.onWebsocketMessage);
        this.refreshStatus();
    },
    beforeUnmount() {
        WebSocketConnection.off("message", this.onWebsocketMessage);
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
        clearRemote() {
            this.remoteHash = "";
            this.activeRemoteHash = "";
            this.refreshStatus();
        },
        onWebsocketMessage(message) {
            let json;
            try {
                json = typeof message === "string" ? JSON.parse(message) : message;
            } catch {
                return;
            }
            if (!json || json.type !== "reticulum_reload_status") {
                return;
            }
            this.reloadingRns = json.in_progress !== false;
            if (json.in_progress === false && json.level !== "error") {
                this.refreshStatus();
            }
        },
        async refreshStatus() {
            if (this.reloadingRns) {
                return;
            }
            this.isLoading = true;
            try {
                const params = {
                    include_link_stats: this.includeLinkStats,
                };
                if (this.sorting) {
                    params.sorting = this.sorting;
                }
                const remote = (this.remoteHash || "").trim();
                if (remote) {
                    params.remote = remote;
                    if (this.identityPath) {
                        params.identity_path = this.identityPath;
                    }
                    if (this.remoteTimeout) {
                        params.timeout = this.remoteTimeout;
                    }
                }
                const response = await window.api.get("/api/v1/rnstatus", { params });
                this.interfaces = response.data.interfaces || [];
                this.linkCount = response.data.link_count;
                this.blackholeEnabled = response.data.blackhole_enabled;
                this.blackholeSources = response.data.blackhole_sources || [];
                this.blackholeCount = response.data.blackhole_count || 0;
                this.activeRemoteHash = response.data.remote || "";
            } catch (e) {
                console.error(e);
                const detail = e?.response?.data?.message || e?.message || "";
                ToastUtils.error(
                    detail ? `${this.$t("rnstatus.failed_refresh")}: ${detail}` : this.$t("rnstatus.failed_refresh")
                );
            } finally {
                this.isLoading = false;
            }
        },
    },
};
</script>
