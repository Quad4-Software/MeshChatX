<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas">
        <ToolsPageHeader
            icon="chart-bar"
            :title="$t('tools.traffic.title')"
            :description="$t('tools.traffic.description')"
            :eyebrow="$t('rnprobe.network_diagnostics')"
            accent="orange"
        >
            <template #actions>
                <button
                    type="button"
                    class="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-sem-border bg-sem-surface text-sm font-medium text-sem-fg hover:bg-sem-surface-muted"
                    @click="togglePause"
                >
                    <MaterialDesignIcon :icon-name="paused ? 'play' : 'pause'" class="h-4 w-4 shrink-0" />
                    <span class="hidden sm:inline">{{ paused ? $t("traffic.resume") : $t("traffic.pause") }}</span>
                </button>
                <button
                    type="button"
                    class="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-sem-warning text-white text-sm font-medium hover:bg-sem-warning disabled:opacity-50 disabled:pointer-events-none"
                    :disabled="isRefreshing"
                    @click="refresh(true)"
                >
                    <MaterialDesignIcon
                        icon-name="refresh"
                        class="h-4 w-4 shrink-0"
                        :class="{ 'animate-spin-reverse': isRefreshing }"
                    />
                    <span class="hidden sm:inline">{{ $t("rnstatus.refresh") }}</span>
                </button>
            </template>
        </ToolsPageHeader>
        <div class="flex-1 overflow-y-auto overflow-x-hidden w-full px-3 sm:px-5 md:px-5 lg:px-8 py-3 sm:py-4 min-w-0">
            <div class="space-y-4 w-full max-w-6xl xl:max-w-7xl mx-auto min-w-0">
                <div
                    v-if="error"
                    class="rounded-xl border border-sem-danger bg-sem-surface p-4 text-sm text-sem-danger"
                >
                    {{ error }}
                </div>

                <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    <div class="rounded-xl border border-sem-border bg-sem-surface p-4">
                        <div class="text-xs text-sem-fg-muted">{{ $t("traffic.upload_rate") }}</div>
                        <div class="text-xl font-semibold text-sem-fg tabular-nums">
                            {{ formatRate(data?.totals?.tx_bps) }}
                        </div>
                    </div>
                    <div class="rounded-xl border border-sem-border bg-sem-surface p-4">
                        <div class="text-xs text-sem-fg-muted">{{ $t("traffic.download_rate") }}</div>
                        <div class="text-xl font-semibold text-sem-fg tabular-nums">
                            {{ formatRate(data?.totals?.rx_bps) }}
                        </div>
                    </div>
                    <div class="rounded-xl border border-sem-border bg-sem-surface p-4">
                        <div class="text-xs text-sem-fg-muted">{{ $t("traffic.total_sent") }}</div>
                        <div class="text-xl font-semibold text-sem-fg tabular-nums">
                            {{ formatBytes(data?.totals?.tx_bytes) }}
                        </div>
                    </div>
                    <div class="rounded-xl border border-sem-border bg-sem-surface p-4">
                        <div class="text-xs text-sem-fg-muted">{{ $t("traffic.total_received") }}</div>
                        <div class="text-xl font-semibold text-sem-fg tabular-nums">
                            {{ formatBytes(data?.totals?.rx_bytes) }}
                        </div>
                    </div>
                </div>

                <div
                    v-if="sparklineTx || sparklineRx"
                    class="relative rounded-xl border border-sem-border bg-sem-surface p-4"
                >
                    <div class="flex items-center justify-between gap-3">
                        <h2 class="text-sm font-semibold text-sem-fg">{{ $t("traffic.recent_activity") }}</h2>
                        <div class="flex items-center gap-4 text-[10px] text-sem-fg-muted">
                            <span class="inline-flex items-center gap-1.5">
                                <span class="inline-block h-2 w-3 rounded-sm bg-sem-warning/60"></span>
                                {{ $t("traffic.upload") }}
                                <span class="tabular-nums text-sem-fg">{{ formatRate(sparkPeak("tx_bps")) }}</span>
                            </span>
                            <span class="inline-flex items-center gap-1.5">
                                <span class="inline-block h-2 w-3 rounded-sm bg-sem-info/60"></span>
                                {{ $t("traffic.download") }}
                                <span class="tabular-nums text-sem-fg">{{ formatRate(sparkPeak("rx_bps")) }}</span>
                            </span>
                            <span
                                v-if="paused"
                                class="inline-flex items-center gap-1 rounded-full border border-sem-warning/60 px-2 py-0.5 text-sem-warning"
                            >
                                {{ $t("traffic.paused") }}
                            </span>
                            <span class="tabular-nums">{{ lastUpdatedLabel }}</span>
                        </div>
                    </div>
                    <p class="mt-1 text-[10px] text-sem-fg-muted">{{ $t("traffic.chart_hint") }}</p>
                    <svg
                        class="mt-2 h-20 w-full cursor-crosshair touch-none"
                        viewBox="0 0 320 80"
                        preserveAspectRatio="none"
                        @mousemove="onSparkMove"
                        @mouseleave="onSparkLeave"
                        @touchstart="onSparkMove"
                        @touchmove="onSparkMove"
                        @touchend="onSparkLeave"
                    >
                        <line
                            v-for="y in [20, 40, 60]"
                            :key="y"
                            x1="0"
                            :y1="y"
                            x2="320"
                            :y2="y"
                            stroke="var(--mc-border)"
                            stroke-width="0.5"
                            stroke-dasharray="3 3"
                        />
                        <polygon
                            v-if="sparkAreaRx"
                            :points="sparkAreaRx"
                            fill="var(--mc-info)"
                            fill-opacity="0.18"
                            stroke="none"
                        />
                        <polygon
                            v-if="sparkAreaTx"
                            :points="sparkAreaTx"
                            fill="var(--mc-warning)"
                            fill-opacity="0.18"
                            stroke="none"
                        />
                        <polyline
                            v-if="sparklineRx"
                            :points="sparklineRx"
                            fill="none"
                            stroke="var(--mc-info)"
                            stroke-width="1.5"
                            stroke-linejoin="round"
                        />
                        <polyline
                            v-if="sparklineTx"
                            :points="sparklineTx"
                            fill="none"
                            stroke="var(--mc-warning)"
                            stroke-width="1.5"
                            stroke-linejoin="round"
                        />
                        <line x1="0" y1="79" x2="320" y2="79" stroke="var(--mc-border)" stroke-width="1" />
                        <template v-if="sparkHover">
                            <line
                                :x1="sparkHover.x"
                                y1="0"
                                :x2="sparkHover.x"
                                y2="79"
                                stroke="var(--mc-fg-muted)"
                                stroke-width="0.5"
                                stroke-dasharray="2 2"
                            />
                            <circle :cx="sparkHover.x" :cy="sparkHover.yTx" r="2.5" fill="var(--mc-warning)" />
                            <circle :cx="sparkHover.x" :cy="sparkHover.yRx" r="2.5" fill="var(--mc-info)" />
                        </template>
                    </svg>
                    <div
                        v-if="sparkHover"
                        class="pointer-events-none absolute top-16 z-10 w-44 rounded-lg border border-sem-border bg-sem-surface p-2 text-xs shadow-lg"
                        :style="sparkTooltipStyle"
                    >
                        <div class="text-sem-fg-muted">{{ sparkHover.time }}</div>
                        <div class="mt-1 flex items-center justify-between gap-2 text-sem-fg">
                            <span class="text-sem-warning">{{ $t("traffic.upload") }}</span>
                            <span class="tabular-nums">{{ formatRate(sparkHover.tx_bps) }}</span>
                        </div>
                        <div class="flex items-center justify-between gap-2 text-sem-fg">
                            <span class="text-sem-info">{{ $t("traffic.download") }}</span>
                            <span class="tabular-nums">{{ formatRate(sparkHover.rx_bps) }}</span>
                        </div>
                        <div v-if="sparkHover.topLabel" class="mt-1 border-t border-sem-border pt-1 text-sem-fg-muted">
                            {{ $t("traffic.driven_by", { component: sparkHover.topLabel }) }}
                        </div>
                    </div>
                </div>

                <div v-if="hints.length" class="rounded-xl border border-sem-border bg-sem-surface p-4 space-y-2">
                    <h2 class="text-sm font-semibold text-sem-fg">{{ $t("traffic.what_is_driving_it") }}</h2>
                    <ul class="space-y-1.5">
                        <li
                            v-for="hint in hints"
                            :key="hint.id"
                            class="flex items-start gap-2 text-sm text-sem-fg-muted"
                        >
                            <MaterialDesignIcon
                                :icon-name="hint.severity === 'warning' ? 'alert-outline' : 'information-outline'"
                                class="h-4 w-4 mt-0.5 shrink-0"
                                :class="hint.severity === 'warning' ? 'text-sem-danger' : 'text-sem-warning'"
                            />
                            <span>{{ hintText(hint) }}</span>
                        </li>
                    </ul>
                </div>

                <div
                    v-if="transferRows.length"
                    class="rounded-xl border border-sem-border bg-sem-surface p-4 space-y-3"
                >
                    <h2 class="text-sm font-semibold text-sem-fg">
                        {{ $t("traffic.active_transfers") }}
                    </h2>
                    <p class="text-xs text-sem-fg-muted">{{ $t("traffic.active_transfers_hint") }}</p>
                    <ul class="space-y-3">
                        <li v-for="row in transferRows" :key="row.id" class="space-y-1.5">
                            <div class="flex items-start justify-between gap-3">
                                <div class="min-w-0">
                                    <div class="truncate text-sm text-sem-fg" :title="row.label">
                                        {{ row.label || componentLabel(row.kind) }}
                                    </div>
                                    <div
                                        v-if="row.peer"
                                        class="truncate font-mono text-xs text-sem-fg-muted"
                                        :title="row.peer"
                                    >
                                        {{ row.peer }}
                                    </div>
                                </div>
                                <div class="shrink-0 text-right text-xs tabular-nums">
                                    <div :class="row.direction === 'rx' ? 'text-sem-info' : 'text-sem-warning'">
                                        {{ row.direction === "rx" ? $t("traffic.download") : $t("traffic.upload") }}
                                        {{ Math.round((row.progress || 0) * 100) }}%
                                    </div>
                                    <div v-if="row.total" class="text-sem-fg-muted">
                                        {{ formatBytes(row.done) }} / {{ formatBytes(row.total) }}
                                    </div>
                                </div>
                            </div>
                            <div class="h-1.5 overflow-hidden rounded bg-sem-surface-muted">
                                <div
                                    class="h-full transition-[width] duration-300"
                                    :class="row.direction === 'rx' ? 'bg-sem-info' : 'bg-sem-warning'"
                                    :style="{ width: Math.round((row.progress || 0) * 100) + '%' }"
                                ></div>
                            </div>
                        </li>
                    </ul>
                </div>

                <div class="rounded-xl border border-sem-border bg-sem-surface p-4 space-y-3">
                    <h2 class="text-sm font-semibold text-sem-fg">{{ $t("traffic.by_component") }}</h2>
                    <p class="text-xs text-sem-fg-muted">{{ $t("traffic.by_component_hint") }}</p>
                    <div class="overflow-x-auto">
                        <table class="w-full text-sm">
                            <thead>
                                <tr class="text-left text-sem-fg-muted">
                                    <th class="pb-2 pr-4 font-medium">{{ $t("traffic.component") }}</th>
                                    <th class="pb-2 pr-4 font-medium text-right">{{ $t("traffic.upload") }}</th>
                                    <th class="pb-2 pr-4 font-medium text-right">{{ $t("traffic.download") }}</th>
                                    <th class="pb-2 pr-4 font-medium text-right">{{ $t("traffic.total_up") }}</th>
                                    <th class="pb-2 font-medium text-right">{{ $t("traffic.total_down") }}</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr
                                    v-for="row in componentRows"
                                    :key="row.id"
                                    class="border-t border-sem-border text-sem-fg"
                                >
                                    <td class="py-2 pr-4">{{ row.label }}</td>
                                    <td class="py-2 pr-4 text-right tabular-nums">{{ formatRate(row.tx_bps) }}</td>
                                    <td class="py-2 pr-4 text-right tabular-nums">{{ formatRate(row.rx_bps) }}</td>
                                    <td class="py-2 pr-4 text-right tabular-nums">{{ formatBytes(row.tx_bytes) }}</td>
                                    <td class="py-2 text-right tabular-nums">{{ formatBytes(row.rx_bytes) }}</td>
                                </tr>
                                <tr class="border-t border-sem-border text-sem-fg-muted">
                                    <td class="py-2 pr-4">{{ $t("traffic.residual") }}</td>
                                    <td class="py-2 pr-4 text-right tabular-nums">
                                        {{ formatRate(data?.residual?.tx_bps) }}
                                    </td>
                                    <td class="py-2 pr-4 text-right tabular-nums">
                                        {{ formatRate(data?.residual?.rx_bps) }}
                                    </td>
                                    <td class="py-2 pr-4 text-right tabular-nums">
                                        {{ formatBytes(data?.residual?.tx_bytes) }}
                                    </td>
                                    <td class="py-2 text-right tabular-nums">
                                        {{ formatBytes(data?.residual?.rx_bytes) }}
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <div v-if="peerRows.length" class="rounded-xl border border-sem-border bg-sem-surface p-4 space-y-3">
                    <h2 class="text-sm font-semibold text-sem-fg">{{ $t("traffic.by_peer") }}</h2>
                    <p class="text-xs text-sem-fg-muted">{{ $t("traffic.by_peer_hint") }}</p>
                    <p v-if="peersNote" class="text-xs text-sem-fg-muted">{{ peersNote }}</p>
                    <div class="overflow-x-auto">
                        <table class="w-full text-sm">
                            <thead>
                                <tr class="text-left text-sem-fg-muted">
                                    <th class="pb-2 pr-4 font-medium">{{ $t("traffic.peer") }}</th>
                                    <th class="pb-2 pr-4 font-medium">{{ $t("traffic.component") }}</th>
                                    <th class="pb-2 pr-4 font-medium text-right">{{ $t("traffic.upload") }}</th>
                                    <th class="pb-2 pr-4 font-medium text-right">{{ $t("traffic.download") }}</th>
                                    <th class="pb-2 pr-4 font-medium text-right">{{ $t("traffic.total_up") }}</th>
                                    <th class="pb-2 font-medium text-right">{{ $t("traffic.total_down") }}</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr
                                    v-for="row in peerRows"
                                    :key="row.hash"
                                    class="border-t border-sem-border text-sem-fg"
                                >
                                    <td class="py-2 pr-4 font-mono text-xs truncate max-w-44" :title="row.hash">
                                        {{ row.hash }}
                                    </td>
                                    <td class="py-2 pr-4 text-sem-fg-muted">{{ peerComponentLabels(row) }}</td>
                                    <td class="py-2 pr-4 text-right tabular-nums">{{ formatRate(row.tx_bps) }}</td>
                                    <td class="py-2 pr-4 text-right tabular-nums">{{ formatRate(row.rx_bps) }}</td>
                                    <td class="py-2 pr-4 text-right tabular-nums">{{ formatBytes(row.tx_bytes) }}</td>
                                    <td class="py-2 text-right tabular-nums">{{ formatBytes(row.rx_bytes) }}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="rounded-xl border border-sem-border bg-sem-surface p-4 space-y-3">
                    <h2 class="text-sm font-semibold text-sem-fg">{{ $t("traffic.by_interface") }}</h2>
                    <div class="overflow-x-auto">
                        <table class="w-full text-sm">
                            <thead>
                                <tr class="text-left text-sem-fg-muted">
                                    <th class="pb-2 pr-4 font-medium">{{ $t("traffic.interface") }}</th>
                                    <th class="pb-2 pr-4 font-medium">{{ $t("traffic.type") }}</th>
                                    <th class="pb-2 pr-4 font-medium text-right">{{ $t("traffic.upload") }}</th>
                                    <th class="pb-2 pr-4 font-medium text-right">{{ $t("traffic.download") }}</th>
                                    <th class="pb-2 pr-4 font-medium text-right">{{ $t("traffic.announces") }}</th>
                                    <th class="pb-2 pr-4 font-medium text-right">{{ $t("traffic.propagated") }}</th>
                                    <th class="pb-2 font-medium text-right">{{ $t("traffic.data") }}</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr
                                    v-for="row in data?.interfaces || []"
                                    :key="row.name"
                                    class="border-t border-sem-border text-sem-fg"
                                >
                                    <td class="py-2 pr-4 truncate max-w-56" :title="row.name">
                                        {{ row.short_name || row.name }}
                                    </td>
                                    <td class="py-2 pr-4 text-sem-fg-muted">{{ row.type }}</td>
                                    <td class="py-2 pr-4 text-right tabular-nums">{{ formatRate(row.tx_bps) }}</td>
                                    <td class="py-2 pr-4 text-right tabular-nums">{{ formatRate(row.rx_bps) }}</td>
                                    <td class="py-2 pr-4 text-right tabular-nums text-sem-fg-muted">
                                        {{ dirRate(row.announce_tx_bps, row.announce_rx_bps) }}
                                    </td>
                                    <td class="py-2 pr-4 text-right tabular-nums text-sem-fg-muted">
                                        {{ dirRate(row.propagated_tx_bps, row.propagated_rx_bps) }}
                                    </td>
                                    <td class="py-2 text-right tabular-nums text-sem-fg-muted">
                                        {{ dirRate(dataRate(row, "tx"), dataRate(row, "rx")) }}
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <p class="text-xs text-sem-fg-muted">
                    {{ $t("traffic.measurement_note") }}
                </p>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToolsPageHeader from "./ToolsPageHeader.vue";
import Utils from "../../js/Utils";
import { apiPath } from "../../js/constants";

const POLL_MS = 3000;

export default {
    name: "TrafficPage",
    components: { MaterialDesignIcon, ToolsPageHeader },
    data() {
        return {
            data: null,
            error: null,
            isLoading: false,
            isRefreshing: false,
            pollTimer: null,
            paused: false,
            sparkHover: null,
        };
    },
    computed: {
        hints() {
            return this.data?.hints || [];
        },
        componentRows() {
            return this.data?.components || [];
        },
        peerRows() {
            return this.data?.peers || [];
        },
        // Both series share one vertical scale so their heights compare
        // honestly. Per-series scaling made a trickle look like a flood.
        sparkGeometry() {
            const rows = this.data?.history || [];
            if (rows.length < 2) {
                return { tx: null, rx: null, areaTx: null, areaRx: null, max: 1, rows };
            }
            let max = 1;
            for (const row of rows) {
                max = Math.max(max, row.tx_bps || 0, row.rx_bps || 0);
            }
            const points = (field) =>
                rows
                    .map((row, i) => {
                        const x = (i / (rows.length - 1)) * 320;
                        const y = 78 - ((row[field] || 0) / max) * 72;
                        return `${x.toFixed(1)},${y.toFixed(1)}`;
                    })
                    .join(" ");
            const tx = points("tx_bps");
            const rx = points("rx_bps");
            return {
                tx,
                rx,
                areaTx: `0,79 ${tx} 320,79`,
                areaRx: `0,79 ${rx} 320,79`,
                max,
                rows,
            };
        },
        sparklineTx() {
            return this.sparkGeometry.tx;
        },
        sparklineRx() {
            return this.sparkGeometry.rx;
        },
        sparkAreaTx() {
            return this.sparkGeometry.areaTx;
        },
        sparkAreaRx() {
            return this.sparkGeometry.areaRx;
        },
        transferRows() {
            return this.data?.transfers || [];
        },
        componentLabels() {
            const map = {};
            for (const row of this.data?.components || []) {
                if (row.id) {
                    map[row.id] = row.label || row.id;
                }
            }
            return map;
        },
        peersNote() {
            const total = this.data?.peers_total || 0;
            const shown = this.peerRows.length;
            if (!total || total <= shown) {
                return "";
            }
            return this.$t("traffic.peers_note", { shown, total });
        },
        sparkTooltipStyle() {
            const pct = this.sparkHover?.pct ?? 0;
            let translate = "-50%";
            if (pct < 18) {
                translate = "0";
            } else if (pct > 82) {
                translate = "-100%";
            }
            return {
                left: `${pct}%`,
                transform: `translateX(${translate})`,
            };
        },
        lastUpdatedLabel() {
            const t = this.data?.updated_at;
            if (!t) return "";
            const ago = Math.max(0, Math.round(Date.now() / 1000 - t));
            return this.$t("traffic.updated_seconds_ago", { s: ago });
        },
    },
    async mounted() {
        await this.refresh();
        this.pollTimer = setInterval(() => {
            if (this.paused) {
                return;
            }
            // A hidden tab has no reader: skip the poll instead of paying
            // for a full payload every interval.
            if (typeof document !== "undefined" && document.hidden) {
                return;
            }
            this.refresh();
        }, POLL_MS);
    },
    beforeUnmount() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
        }
    },
    methods: {
        async refresh(manual = false) {
            if (this.isLoading) return;
            this.isLoading = true;
            if (manual) {
                this.isRefreshing = true;
            }
            try {
                const response = await window.api.get(apiPath("/reticulum/traffic"));
                this.data = response?.data || null;
                this.error = null;
            } catch {
                this.error = this.$t("traffic.load_failed");
            } finally {
                this.isLoading = false;
                this.isRefreshing = false;
            }
        },
        sparkPeak(field) {
            const rows = this.data?.history || [];
            if (!rows.length) return 0;
            return Math.max(...rows.map((r) => r[field] || 0));
        },
        onSparkMove(event) {
            const rows = this.sparkGeometry.rows;
            if (rows.length < 2) {
                this.sparkHover = null;
                return;
            }
            const svg = event.currentTarget;
            const rect = svg?.getBoundingClientRect?.();
            if (!rect || !rect.width) {
                return;
            }
            const touch = event.touches && event.touches[0];
            const clientX = touch ? touch.clientX : event.clientX;
            if (typeof clientX !== "number") {
                return;
            }
            const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
            const index = Math.round(ratio * (rows.length - 1));
            const row = rows[index];
            if (!row) {
                return;
            }
            const max = this.sparkGeometry.max;
            const y = (value) => 78 - ((value || 0) / max) * 72;
            const at = row.t
                ? new Date(row.t * 1000).toLocaleTimeString()
                : this.$t("traffic.updated_seconds_ago", { s: 0 });
            this.sparkHover = {
                index,
                pct: ratio * 100,
                x: (index / (rows.length - 1)) * 320,
                yTx: y(row.tx_bps),
                yRx: y(row.rx_bps),
                tx_bps: row.tx_bps || 0,
                rx_bps: row.rx_bps || 0,
                time: at,
                topLabel: row.top ? this.componentLabel(row.top) : "",
            };
        },
        onSparkLeave() {
            this.sparkHover = null;
        },
        componentLabel(id) {
            if (!id) {
                return "";
            }
            const key = `traffic.components.${id}`;
            const translated = this.$t(key);
            return translated === key ? this.componentLabels[id] || id : translated;
        },
        togglePause() {
            this.paused = !this.paused;
        },
        dirRate(up, down) {
            return `${this.formatRate(up || 0)} / ${this.formatRate(down || 0)}`;
        },
        dataRate(row, dir) {
            // interface payload = total minus announce and propagated bytes
            const total = dir === "tx" ? row.tx_bps || 0 : row.rx_bps || 0;
            const overhead =
                (dir === "tx" ? row.announce_tx_bps || 0 : row.announce_rx_bps || 0) +
                (dir === "tx" ? row.propagated_tx_bps || 0 : row.propagated_rx_bps || 0);
            return Math.max(0, total - overhead);
        },
        peerComponentLabels(row) {
            const comps = row.components || {};
            return Object.keys(comps)
                .filter((k) => comps[k] && (comps[k].tx || comps[k].rx))
                .map((k) => this.componentLabel(k))
                .join(", ");
        },
        formatBytes(value) {
            return Utils.formatBytes(value || 0);
        },
        formatRate(value) {
            return Utils.formatBytesPerSecond(value || 0);
        },
        hintText(hint) {
            const key = `traffic.hints.${hint.id}`;
            const params = hint.params || {};
            const translated = this.$t(key, params);
            return translated === key ? hint.id : translated;
        },
    },
};
</script>
