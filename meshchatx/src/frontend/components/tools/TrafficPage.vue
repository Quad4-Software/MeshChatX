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
                    :disabled="isLoading"
                    @click="refresh"
                >
                    <MaterialDesignIcon
                        icon-name="refresh"
                        class="h-4 w-4 shrink-0"
                        :class="{ 'animate-spin-reverse': isLoading }"
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

                <div v-if="sparklineTx || sparklineRx" class="rounded-xl border border-sem-border bg-sem-surface p-4">
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
                    <svg class="mt-2 h-20 w-full" viewBox="0 0 320 80" preserveAspectRatio="none">
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
                    </svg>
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
                                icon-name="information-outline"
                                class="h-4 w-4 mt-0.5 shrink-0 text-sem-warning"
                            />
                            <span>{{ hintText(hint) }}</span>
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
            pollTimer: null,
            paused: false,
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
        sparklineTx() {
            return this.sparkPoints("tx_bps");
        },
        sparklineRx() {
            return this.sparkPoints("rx_bps");
        },
        sparkAreaTx() {
            return this.sparkArea("tx_bps");
        },
        sparkAreaRx() {
            return this.sparkArea("rx_bps");
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
            if (!this.paused) this.refresh();
        }, POLL_MS);
    },
    beforeUnmount() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
        }
    },
    methods: {
        async refresh() {
            if (this.isLoading) return;
            this.isLoading = true;
            try {
                const response = await window.api.get(apiPath("/reticulum/traffic"));
                this.data = response?.data || null;
                this.error = null;
            } catch {
                this.error = this.$t("traffic.load_failed");
            } finally {
                this.isLoading = false;
            }
        },
        sparkMax(field) {
            const rows = this.data?.history || [];
            return Math.max(...rows.map((r) => r[field] || 0), 1);
        },
        sparkPeak(field) {
            const rows = this.data?.history || [];
            if (!rows.length) return 0;
            return Math.max(...rows.map((r) => r[field] || 0));
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
            const order = ["lxmf", "rrc", "nomadnet", "crawler"];
            const labels = {
                lxmf: this.$t("traffic.components.lxmf"),
                rrc: this.$t("traffic.components.rrc"),
                nomadnet: this.$t("traffic.components.nomadnet"),
                crawler: this.$t("traffic.components.crawler"),
            };
            const comps = row.components || {};
            return order
                .filter((k) => comps[k] && (comps[k].tx || comps[k].rx))
                .map((k) => labels[k] || k)
                .join(", ");
        },
        sparkPoints(field) {
            const rows = this.data?.history || [];
            if (rows.length < 2) return null;
            const max = this.sparkMax(field);
            return rows
                .map((r, i) => {
                    const x = (i / (rows.length - 1)) * 320;
                    const y = 78 - ((r[field] || 0) / max) * 72;
                    return `${x.toFixed(1)},${y.toFixed(1)}`;
                })
                .join(" ");
        },
        sparkArea(field) {
            const points = this.sparkPoints(field);
            if (!points) return null;
            return `0,79 ${points} 320,79`;
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
