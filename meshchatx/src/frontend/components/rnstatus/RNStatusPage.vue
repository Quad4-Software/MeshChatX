<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas">
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
            <div class="space-y-4 w-full max-w-6xl xl:max-w-7xl mx-auto min-w-0">
                <div class="rounded-xl border border-sem-border bg-sem-surface p-4 space-y-3">
                    <div class="flex flex-wrap items-center gap-3">
                        <label
                            class="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-sem-border bg-sem-canvas px-3 py-2 text-sm text-sem-fg"
                        >
                            <input
                                v-model="includeLinkStats"
                                type="checkbox"
                                class="rounded-sm"
                                :disabled="reloadingRns"
                            />
                            <span>{{ $t("rnstatus.include_link_stats") }}</span>
                        </label>
                        <label
                            class="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-sem-border bg-sem-canvas px-3 py-2 text-sm text-sem-fg"
                        >
                            <input v-model="showAll" type="checkbox" class="rounded-sm" :disabled="reloadingRns" />
                            <span>{{ $t("rnstatus.show_all_interfaces") }}</span>
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
                                <option value="prx">{{ $t("rnstatus.path_requests") }}</option>
                                <option value="held">{{ $t("rnstatus.held_announces") }}</option>
                                <option value="gravity">{{ $t("rnstatus.gravity") }}</option>
                            </select>
                        </div>
                    </div>
                </div>

                <div class="rounded-xl border border-sem-border bg-sem-surface p-4 space-y-3">
                    <h2 class="text-sm font-semibold text-sem-fg">
                        {{ $t("rnstatus.remote_query") }}
                    </h2>
                    <p class="text-xs text-sem-fg-muted">
                        {{ $t("rnstatus.remote_query_hint") }}
                    </p>
                    <div class="grid gap-3 lg:grid-cols-2">
                        <label class="block space-y-1">
                            <span class="text-xs font-medium text-sem-fg-muted">{{
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
                            <span class="text-xs font-medium text-sem-fg-muted">{{
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
                            class="inline-flex items-center px-2 py-1 rounded-lg border border-gray-300 dark:border-zinc-600 bg-sem-surface text-xs font-medium text-sem-fg hover:bg-sem-surface-muted"
                            @click="clearRemote"
                        >
                            {{ $t("rnstatus.use_local") }}
                        </button>
                    </div>
                </div>

                <div v-if="hasSummary" class="grid grid-cols-2 gap-3 lg:grid-cols-4">
                    <div v-if="linkCount !== null" class="rounded-xl border border-sem-border bg-sem-surface p-4">
                        <div class="text-xs uppercase tracking-wide text-sem-fg-muted">
                            {{ $t("rnstatus.active_links_label") }}
                        </div>
                        <div class="mt-1 text-2xl font-semibold tabular-nums text-sem-fg">
                            {{ formatInt(linkCount) }}
                        </div>
                        <div v-if="activeLinkCount !== null" class="text-xs text-sem-fg-muted tabular-nums">
                            {{
                                $t("rnstatus.active_links_detail", {
                                    active: formatInt(activeLinkCount),
                                    total: formatInt(linkCount),
                                })
                            }}
                        </div>
                    </div>
                    <div v-if="rnsVersion" class="rounded-xl border border-sem-border bg-sem-surface p-4">
                        <div class="text-xs uppercase tracking-wide text-sem-fg-muted">
                            {{ $t("rnstatus.rns_version") }}
                        </div>
                        <div class="mt-1 text-lg font-semibold text-sem-fg">
                            {{ rnsVersion }}
                        </div>
                    </div>
                    <div v-if="transportUptimeStr" class="rounded-xl border border-sem-border bg-sem-surface p-4">
                        <div class="text-xs uppercase tracking-wide text-sem-fg-muted">
                            {{ $t("rnstatus.uptime") }}
                        </div>
                        <div class="mt-1 text-lg font-semibold text-sem-fg">
                            {{ transportUptimeStr }}
                        </div>
                    </div>
                    <div v-if="totals" class="rounded-xl border border-sem-border bg-sem-surface p-4">
                        <div class="text-xs uppercase tracking-wide text-sem-fg-muted">
                            {{ $t("rnstatus.totals") }}
                        </div>
                        <div class="mt-1 text-sm font-semibold tabular-nums text-sem-fg">
                            <div>↑ {{ totals.tx_bytes_str }} {{ totals.tx_speed_str }}</div>
                            <div>↓ {{ totals.rx_bytes_str }} {{ totals.rx_speed_str }}</div>
                        </div>
                    </div>
                    <div
                        v-if="blackholeEnabled !== null"
                        class="rounded-xl border border-sem-border bg-sem-surface p-4"
                    >
                        <div class="text-xs uppercase tracking-wide text-sem-fg-muted">
                            {{ $t("rnstatus.blackhole_heading") }}
                        </div>
                        <div class="mt-1 text-lg font-semibold text-sem-fg">
                            {{
                                blackholeEnabled
                                    ? $t("rnstatus.blackhole_publishing")
                                    : $t("rnstatus.blackhole_inactive")
                            }}
                        </div>
                        <div class="text-xs text-sem-fg-muted tabular-nums">
                            {{ $t("rnstatus.blackhole_identities", { count: formatInt(blackholeCount) }) }}
                        </div>
                    </div>
                    <div v-if="rssStr" class="rounded-xl border border-sem-border bg-sem-surface p-4">
                        <div class="text-xs uppercase tracking-wide text-sem-fg-muted">
                            {{ $t("rnstatus.memory_rss") }}
                        </div>
                        <div class="mt-1 text-lg font-semibold text-sem-fg">
                            {{ rssStr }}
                        </div>
                    </div>
                </div>

                <div v-if="totalsAnnounces || totalsPathRequests" class="grid gap-3 lg:grid-cols-2">
                    <div
                        v-if="totalsAnnounces"
                        class="rounded-xl border border-sem-border bg-sem-surface p-4 space-y-2"
                    >
                        <h2 class="text-sm font-semibold text-sem-fg">
                            {{ $t("rnstatus.transport_announces") }}
                        </h2>
                        <div class="text-sm tabular-nums text-sem-fg">
                            <div>↑ {{ totalsAnnounces.tx_bytes_str }} {{ totalsAnnounces.tx_speed_str }}</div>
                            <div>↓ {{ totalsAnnounces.rx_bytes_str }} {{ totalsAnnounces.rx_speed_str }}</div>
                        </div>
                    </div>
                    <div
                        v-if="totalsPathRequests"
                        class="rounded-xl border border-sem-border bg-sem-surface p-4 space-y-2"
                    >
                        <h2 class="text-sm font-semibold text-sem-fg">
                            {{ $t("rnstatus.transport_path_requests") }}
                        </h2>
                        <div class="text-sm tabular-nums text-sem-fg">
                            <div>↑ {{ totalsPathRequests.tx_bytes_str }} {{ totalsPathRequests.tx_speed_str }}</div>
                            <div>↓ {{ totalsPathRequests.rx_bytes_str }} {{ totalsPathRequests.rx_speed_str }}</div>
                        </div>
                    </div>
                </div>

                <div
                    v-if="queueRows.length > 0"
                    class="rounded-xl border border-sem-border bg-sem-surface p-4 space-y-3"
                >
                    <h2 class="text-sm font-semibold text-sem-fg">
                        {{ $t("rnstatus.queue_pressure") }}
                    </h2>
                    <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                        <div
                            v-for="queue in queueRows"
                            :key="queue.key"
                            class="rounded-lg border border-sem-border bg-sem-canvas p-3"
                        >
                            <div class="text-xs font-semibold uppercase tracking-wide text-sem-fg-muted">
                                {{ queue.label }}
                            </div>
                            <div class="mt-1 text-sm font-semibold text-sem-fg">
                                {{ queue.pressure || "—" }}
                            </div>
                            <div class="text-xs text-sem-fg-muted">
                                <span v-if="queue.packets">
                                    {{ $t("rnstatus.queue_packets", { count: queue.packets }) }}
                                </span>
                                <span v-if="queue.dropped" class="ml-2">
                                    {{ $t("rnstatus.queue_dropped", { count: queue.dropped }) }}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                <div
                    v-if="transportId || networkId || probeResponder"
                    class="rounded-xl border border-sem-border bg-sem-surface p-4 space-y-3"
                >
                    <h2 class="text-sm font-semibold text-sem-fg">
                        {{ $t("rnstatus.transport_instance") }}
                    </h2>
                    <div class="grid gap-3 md:grid-cols-2">
                        <div v-if="transportId" class="address-card">
                            <div class="address-card__label">{{ $t("rnstatus.transport_id") }}</div>
                            <div class="address-card__value monospace-field">{{ transportId }}</div>
                            <button type="button" class="address-card__action" @click="copyText(transportId)">
                                <MaterialDesignIcon icon-name="content-copy" class="w-3.5 h-3.5" />
                                {{ $t("common.copy") }}
                            </button>
                        </div>
                        <div v-if="networkId" class="address-card">
                            <div class="address-card__label">{{ $t("rnstatus.network_id") }}</div>
                            <div class="address-card__value monospace-field">{{ networkId }}</div>
                            <button type="button" class="address-card__action" @click="copyText(networkId)">
                                <MaterialDesignIcon icon-name="content-copy" class="w-3.5 h-3.5" />
                                {{ $t("common.copy") }}
                            </button>
                        </div>
                        <div v-if="probeResponder" class="address-card">
                            <div class="address-card__label">{{ $t("rnstatus.probe_responder") }}</div>
                            <div class="address-card__value monospace-field">{{ probeResponder }}</div>
                            <button type="button" class="address-card__action" @click="copyText(probeResponder)">
                                <MaterialDesignIcon icon-name="content-copy" class="w-3.5 h-3.5" />
                                {{ $t("common.copy") }}
                            </button>
                        </div>
                    </div>
                </div>

                <div
                    v-if="i2pInterfaces.length > 0"
                    class="rounded-xl border border-violet-200 dark:border-violet-900/60 bg-violet-50 dark:bg-violet-950/30 p-4 space-y-3"
                >
                    <h2 class="text-sm font-semibold text-violet-950 dark:text-violet-100">
                        {{ $t("rnstatus.i2p_address") }}
                    </h2>
                    <div v-for="iface in i2pInterfaces" :key="'i2p-' + iface.name" class="space-y-2">
                        <div class="text-xs text-violet-800 dark:text-violet-200">{{ iface.name }}</div>
                        <div v-if="iface.i2p_b32" class="address-card">
                            <div class="address-card__label">{{ $t("rnstatus.i2p_address") }}</div>
                            <div class="address-card__value monospace-field">{{ iface.i2p_b32 }}</div>
                            <button type="button" class="address-card__action" @click="copyText(iface.i2p_b32)">
                                <MaterialDesignIcon icon-name="content-copy" class="w-3.5 h-3.5" />
                                {{ $t("common.copy") }}
                            </button>
                        </div>
                        <p v-else-if="iface.i2p_connectable" class="text-sm text-violet-900 dark:text-violet-100">
                            {{ $t("rnstatus.i2p_waiting") }}
                        </p>
                        <p v-else class="text-sm text-violet-900 dark:text-violet-100">
                            {{ $t("rnstatus.i2p_not_published") }}
                        </p>
                        <div class="flex flex-wrap gap-2 text-xs">
                            <span
                                class="rounded-full px-2 py-0.5 font-medium"
                                :class="
                                    iface.i2p_connectable
                                        ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-100'
                                        : 'bg-gray-200 text-gray-700 dark:bg-zinc-800 text-sem-fg'
                                "
                            >
                                {{
                                    iface.i2p_connectable
                                        ? $t("rnstatus.i2p_connectable_yes")
                                        : $t("rnstatus.i2p_connectable_no")
                                }}
                            </span>
                            <span
                                v-if="iface.i2p_tunnel_state"
                                class="rounded-full bg-white/70 dark:bg-zinc-900/70 px-2 py-0.5 font-medium text-violet-900 dark:text-violet-100"
                            >
                                {{ iface.i2p_tunnel_state }}
                            </span>
                        </div>
                    </div>
                </div>

                <div
                    v-if="blackholeSources.length > 0"
                    class="rounded-xl border border-sem-border bg-sem-surface p-4 space-y-3"
                >
                    <h2 class="text-sm font-semibold text-sem-fg">
                        {{ $t("rnstatus.blackhole_sources") }}
                    </h2>
                    <div class="divide-y divide-gray-100 dark:divide-zinc-800/50">
                        <div
                            v-for="source in blackholeSources"
                            :key="source"
                            class="py-2 text-sm font-mono text-sem-fg truncate"
                        >
                            {{ source }}
                        </div>
                    </div>
                </div>

                <div
                    v-if="interfaces.length === 0 && !isLoading && !reloadingRns"
                    class="rounded-xl border border-dashed border-gray-300 dark:border-zinc-700 py-12 text-center text-sm text-sem-fg-muted"
                >
                    {{ $t("rnstatus.no_interfaces_found") }}
                </div>

                <div v-else class="space-y-3">
                    <div
                        v-for="iface in interfaces"
                        :key="iface.name"
                        class="rounded-xl border border-sem-border bg-sem-surface p-4 sm:p-5 space-y-4"
                    >
                        <div class="flex flex-wrap items-start justify-between gap-3">
                            <div class="min-w-0 flex-1 space-y-1">
                                <div class="flex flex-wrap items-center gap-2">
                                    <h3 class="wrap-break-word text-base font-semibold leading-snug text-sem-fg">
                                        {{ iface.name }}
                                    </h3>
                                    <span
                                        v-if="iface.discovered"
                                        class="inline-flex shrink-0 items-center rounded-md bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-900 dark:bg-amber-900/45 dark:text-amber-100"
                                    >
                                        {{ $t("rnstatus.discovered") }}
                                    </span>
                                </div>
                                <div v-if="iface.type" class="text-xs text-sem-fg-muted">
                                    {{ iface.type }}
                                </div>
                            </div>
                            <span
                                :class="[
                                    iface.status && String(iface.status).startsWith('Up')
                                        ? 'bg-green-100 text-green-800 dark:bg-green-900/45 dark:text-green-100'
                                        : 'bg-red-100 text-red-800 dark:bg-red-900/45 dark:text-red-100',
                                    'shrink-0 rounded-full px-3 py-1 text-xs font-semibold',
                                ]"
                            >
                                {{ iface.status }}
                            </span>
                        </div>

                        <div v-if="iface.i2p_b32" class="address-card">
                            <div class="address-card__label">{{ $t("rnstatus.i2p_address") }}</div>
                            <div class="address-card__value monospace-field">{{ iface.i2p_b32 }}</div>
                            <button type="button" class="address-card__action" @click="copyText(iface.i2p_b32)">
                                <MaterialDesignIcon icon-name="content-copy" class="w-3.5 h-3.5" />
                                {{ $t("common.copy") }}
                            </button>
                        </div>

                        <div class="grid gap-x-6 gap-y-3 text-sm md:grid-cols-2 lg:grid-cols-3">
                            <div v-for="row in ifaceStatRows(iface)" :key="iface.name + '-' + row.key">
                                <div class="text-xs text-sem-fg-muted">{{ row.label }}</div>
                                <div class="font-semibold tabular-nums text-sem-fg wrap-break-word">
                                    {{ row.value }}
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
import { onWsEvent, offWsEvent } from "../../js/registries/wsEventRegistry.js";

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
            showAll: false,
            sorting: "",
            blackholeEnabled: null,
            blackholeSources: [],
            blackholeCount: 0,
            remoteHash: "",
            identityPath: "",
            remoteTimeout: 15,
            activeRemoteHash: "",
            transportId: "",
            networkId: "",
            probeResponder: "",
            transportUptimeStr: "",
            totals: null,
            totalsAnnounces: null,
            totalsPathRequests: null,
            queues: null,
            rnsVersion: "",
            activeLinkCount: null,
            rssStr: "",
        };
    },
    computed: {
        hasSummary() {
            return (
                this.linkCount !== null ||
                Boolean(this.transportUptimeStr) ||
                Boolean(this.totals) ||
                this.blackholeEnabled !== null ||
                Boolean(this.rnsVersion) ||
                Boolean(this.rssStr)
            );
        },
        queueRows() {
            const queues = this.queues?.queues;
            if (!Array.isArray(queues)) {
                return [];
            }
            const labels = {
                total: this.$t("rnstatus.queue_total"),
                data: this.$t("rnstatus.queue_data"),
                announce: this.$t("rnstatus.queue_announce"),
                path_request: this.$t("rnstatus.queue_path_request"),
                ingress_limiter: this.$t("rnstatus.queue_ingress_limiter"),
            };
            return queues.map((queue) => ({
                key: queue.name,
                label: labels[queue.name] || queue.name,
                pressure: queue.pressure,
                packets: queue.packets,
                dropped: queue.dropped,
            }));
        },
        i2pInterfaces() {
            return (this.interfaces || []).filter(
                (iface) => iface.i2p_b32 || iface.i2p_connectable === true || iface.i2p_connectable === false
            );
        },
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
        showAll() {
            if (!this.reloadingRns) {
                this.refreshStatus();
            }
        },
    },
    mounted() {
        onWsEvent("reticulum_reload_status", this.onReloadStatus);
        this.refreshStatus();
    },
    beforeUnmount() {
        offWsEvent("reticulum_reload_status", this.onReloadStatus);
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
        ifaceStatRows(iface) {
            const rows = [];
            const add = (key, value) => {
                if (value === undefined || value === null || value === "") {
                    return;
                }
                rows.push({ key, label: this.$t(`rnstatus.${key}`), value });
            };
            add("mode", iface.mode);
            add("bitrate", iface.bitrate);
            add("rx_bytes", iface.rx_bytes_str);
            add("tx_bytes", iface.tx_bytes_str);
            add("rx_speed", iface.rx_speed_str);
            add("tx_speed", iface.tx_speed_str);
            if (iface.clients !== undefined) {
                add("clients", this.formatInt(iface.clients));
            }
            if (iface.peers !== undefined) {
                add("peers", `${this.formatInt(iface.peers)} ${this.$t("rnstatus.peers_reachable")}`);
            }
            add("noise_floor", iface.noise_floor);
            add("interference", iface.interference);
            add("interference_last", iface.interference_last);
            add("cpu_load", iface.cpu_load);
            add("cpu_temp", iface.cpu_temp);
            add("memory_load", iface.mem_load);
            if (iface.battery_percent !== undefined) {
                const battery = `${this.formatInt(iface.battery_percent)}%`;
                add("battery", iface.battery_state ? `${battery} (${iface.battery_state})` : battery);
            }
            add("network", iface.network_name);
            if (iface.incoming_announce_frequency !== undefined) {
                add("incoming_announces", `${iface.incoming_announce_frequency}/s`);
            }
            if (iface.outgoing_announce_frequency !== undefined) {
                add("outgoing_announces", `${iface.outgoing_announce_frequency}/s`);
            }
            if (iface.incoming_pr_frequency !== undefined) {
                add("path_requests_in", `${iface.incoming_pr_frequency}/s`);
            }
            if (iface.outgoing_pr_frequency !== undefined) {
                add("path_requests_out", `${iface.outgoing_pr_frequency}/s`);
            }
            add("held_announces", iface.held_announces);
            add("announce_queue", iface.announce_queue);
            add("announce_totals", iface.announce_totals);
            add("path_request_totals", iface.path_request_totals);
            add("announce_rx_bytes", iface.announce_rx_bytes_str);
            add("announce_tx_bytes", iface.announce_tx_bytes_str);
            add("path_rx_bytes", iface.path_rx_bytes_str);
            add("path_tx_bytes", iface.path_tx_bytes_str);
            if (iface.announce_flow_rx_pct !== undefined) {
                add("announce_flow_rx", this.$t("rnstatus.flow_share", { pct: iface.announce_flow_rx_pct }));
            }
            if (iface.announce_flow_tx_pct !== undefined) {
                add("announce_flow_tx", this.$t("rnstatus.flow_share", { pct: iface.announce_flow_tx_pct }));
            }
            if (iface.path_flow_rx_pct !== undefined) {
                add("path_flow_rx", this.$t("rnstatus.flow_share", { pct: iface.path_flow_rx_pct }));
            }
            if (iface.path_flow_tx_pct !== undefined) {
                add("path_flow_tx", this.$t("rnstatus.flow_share", { pct: iface.path_flow_tx_pct }));
            }
            add("announce_rate_limits", iface.announce_rate_limits);
            add("violations", iface.violations);
            add("filter_hits", iface.filter_hits);
            if (Array.isArray(iface.blocked_ip_list) && iface.blocked_ip_list.length > 0) {
                add("blocked_ip_list", iface.blocked_ip_list.join(", "));
            }
            if (iface.airtime) {
                add("airtime", `${iface.airtime.short}% (15s), ${iface.airtime.long}% (1h)`);
            }
            if (iface.channel_load) {
                add("channel_load", `${iface.channel_load.short}% (15s), ${iface.channel_load.long}% (1h)`);
            }
            add("i2p_tunnel", iface.i2p_tunnel_state);
            add("switch_id", iface.switch_id);
            add("endpoint_id", iface.endpoint_id);
            add("via_switch", iface.via_switch_id);
            add("access_ifac", iface.ifac_access);
            add("parent_interface", iface.parent_interface);
            add("autoconnect_source", iface.autoconnect_source);
            add("blocked_ips", iface.blocked_ips);
            add("burst", iface.burst);
            add("path_burst", iface.path_burst);
            return rows;
        },
        clearRemote() {
            this.remoteHash = "";
            this.activeRemoteHash = "";
            this.refreshStatus();
        },
        async copyText(value) {
            if (!value) {
                return;
            }
            try {
                await navigator.clipboard.writeText(value);
                ToastUtils.success(this.$t("common.copied"));
            } catch {
                ToastUtils.error(this.$t("common.failed_to_copy"));
            }
        },
        onReloadStatus(json) {
            this.reloadingRns = json.in_progress !== false;
            if (json.in_progress === false && json.level !== "error") {
                this.refreshStatus();
            }
        },
        onWebsocketMessage(message) {
            let json;
            try {
                if (
                    message &&
                    typeof message === "object" &&
                    typeof message.type === "string" &&
                    message.data === undefined
                ) {
                    json = message;
                } else {
                    const raw = typeof message === "string" ? message : message?.data;
                    json = typeof raw === "string" ? JSON.parse(raw) : message;
                }
            } catch {
                return;
            }
            if (!json || typeof json !== "object" || typeof json.type !== "string") {
                return;
            }
            if (json.type === "reticulum_reload_status") {
                return this.onReloadStatus(json);
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
                    show_all: this.showAll,
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
                const data = response.data || {};
                this.interfaces = data.interfaces || [];
                this.linkCount = data.link_count;
                this.blackholeEnabled = data.blackhole_enabled;
                this.blackholeSources = data.blackhole_sources || [];
                this.blackholeCount = data.blackhole_count || 0;
                this.activeRemoteHash = data.remote || "";
                this.transportId = data.transport_id || "";
                this.networkId = data.network_id || "";
                this.probeResponder = data.probe_responder || "";
                this.transportUptimeStr = data.transport_uptime_str || "";
                this.totals = data.totals || null;
                this.totalsAnnounces = data.totals?.announces || null;
                this.totalsPathRequests = data.totals?.path_requests || null;
                this.queues = data.queues || null;
                this.rnsVersion = data.rns_version || "";
                this.activeLinkCount =
                    data.active_link_count === undefined || data.active_link_count === null
                        ? null
                        : data.active_link_count;
                this.rssStr = data.rss_str || "";
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
