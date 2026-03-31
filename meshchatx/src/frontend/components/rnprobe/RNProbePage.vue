<template>
    <div
        class="flex flex-col flex-1 overflow-hidden min-w-0 bg-gradient-to-br from-slate-50 via-slate-100 to-white dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-900"
    >
        <div class="flex-1 overflow-y-auto w-full px-4 md:px-8 py-6">
            <div class="space-y-4 w-full max-w-4xl mx-auto">
                <div class="glass-card space-y-5">
                    <div class="space-y-2">
                        <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                            {{ $t("rnprobe.network_diagnostics") }}
                        </div>
                        <div class="text-2xl font-semibold text-gray-900 dark:text-white">
                            {{ $t("rnprobe.title") }}
                        </div>
                        <div class="text-sm text-gray-600 dark:text-gray-300">
                            {{ $t("rnprobe.description") }}
                        </div>
                    </div>

                    <div class="grid md:grid-cols-2 gap-4">
                        <div>
                            <label class="glass-label">{{ $t("rnprobe.destination_hash") }}</label>
                            <input
                                v-model="destinationHash"
                                type="text"
                                placeholder="e.g. 7b746057a7294469799cd8d7d429676a"
                                class="input-field font-mono"
                            />
                        </div>
                        <div>
                            <label class="glass-label">{{ $t("rnprobe.full_destination_name") }}</label>
                            <input
                                v-model="fullName"
                                type="text"
                                placeholder="e.g. lxmf.delivery"
                                class="input-field"
                            />
                        </div>
                    </div>

                    <div class="grid md:grid-cols-3 gap-4">
                        <div>
                            <label class="glass-label">{{ $t("rnprobe.probe_size_bytes") }}</label>
                            <input v-model="probeSize" type="number" min="1" max="1024" class="input-field" />
                        </div>
                        <div>
                            <label class="glass-label">{{ $t("rnprobe.number_of_probes") }}</label>
                            <input v-model="probes" type="number" min="1" max="100" class="input-field" />
                        </div>
                        <div>
                            <label class="glass-label">{{ $t("rnprobe.wait_between_probes") }}</label>
                            <input v-model="wait" type="number" min="0" step="0.1" class="input-field" />
                        </div>
                    </div>

                    <div class="flex gap-2">
                        <button
                            v-if="!isRunning"
                            type="button"
                            class="primary-chip px-4 py-2 text-sm"
                            @click="startProbe"
                        >
                            <MaterialDesignIcon icon-name="radar" class="w-4 h-4" />
                            {{ $t("rnprobe.start_probe") }}
                        </button>
                        <button
                            v-else
                            type="button"
                            class="secondary-chip px-4 py-2 text-sm text-red-600 dark:text-red-300 border-red-200 dark:border-red-500/50"
                            @click="stopProbe"
                        >
                            <MaterialDesignIcon icon-name="stop" class="w-4 h-4" />
                            {{ $t("rnprobe.stop") }}
                        </button>
                        <button type="button" class="secondary-chip px-4 py-2 text-sm" @click="clearResults">
                            <MaterialDesignIcon icon-name="broom" class="w-4 h-4" />
                            {{ $t("rnprobe.clear_results") }}
                        </button>
                    </div>

                    <div
                        v-if="summary"
                        class="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300"
                    >
                        <div class="font-semibold">{{ $t("rnprobe.summary") }}:</div>
                        <div class="text-sm mt-1">
                            {{ $t("rnprobe.sent") }}: {{ summary.sent }}, {{ $t("rnprobe.delivered") }}:
                            {{ summary.delivered }}, {{ $t("rnprobe.timeouts") }}: {{ summary.timeouts }},
                            {{ $t("rnprobe.failed") }}:
                            {{ summary.failed }}
                        </div>
                    </div>
                </div>

                <div class="glass-card flex flex-col min-h-[320px] space-y-3">
                    <div class="flex items-center justify-between gap-4">
                        <div>
                            <div class="text-sm font-semibold text-gray-900 dark:text-white">
                                {{ $t("rnprobe.probe_results") }}
                            </div>
                            <div class="text-xs text-gray-500 dark:text-gray-400">
                                {{ $t("rnprobe.probe_responses_realtime") }}
                            </div>
                        </div>
                    </div>

                    <div
                        class="flex-1 overflow-y-auto rounded-2xl bg-black/80 text-emerald-300 font-mono text-xs p-3 space-y-2 shadow-inner border border-zinc-900"
                    >
                        <div v-if="results.length === 0" class="text-emerald-500/80">
                            {{ $t("rnprobe.no_probes_yet") }}
                        </div>
                        <div v-for="(result, index) in results" :key="index" class="space-y-1">
                            <div class="flex items-center gap-2">
                                <span class="text-emerald-400">{{
                                    $t("rnprobe.probe_number", { number: result.probe_number })
                                }}</span>
                                <span class="text-gray-400">({{ result.size }} {{ $t("rnprobe.bytes") }})</span>
                                <span class="text-gray-400">→</span>
                                <span class="text-emerald-300">{{ result.destination }}</span>
                            </div>
                            <div v-if="result.via || result.interface" class="text-gray-500 ml-4">
                                {{ result.via }}{{ result.interface }}
                            </div>
                            <div v-if="result.status === 'delivered'" class="text-green-400 ml-4 space-y-1">
                                <div>{{ $t("rnprobe.summary") }}: {{ $t("rnprobe.delivered") }}</div>
                                <div>{{ $t("rnprobe.hops") }}: {{ result.hops }}</div>
                                <div>{{ $t("rnprobe.rtt") }}: {{ result.rtt_string }}</div>
                                <div v-if="result.reception_stats" class="space-x-2">
                                    <span v-if="result.reception_stats.rssi"
                                        >{{ $t("rnprobe.rssi") }}: {{ result.reception_stats.rssi }} dBm</span
                                    >
                                    <span v-if="result.reception_stats.snr"
                                        >{{ $t("rnprobe.snr") }}: {{ result.reception_stats.snr }} dB</span
                                    >
                                    <span v-if="result.reception_stats.quality"
                                        >{{ $t("rnprobe.quality") }}: {{ result.reception_stats.quality }}%</span
                                    >
                                </div>
                            </div>
                            <div v-else-if="result.status === 'timeout'" class="text-yellow-400 ml-4">
                                {{ $t("rnprobe.summary") }}: {{ $t("rnprobe.timeout") }}
                            </div>
                            <div v-else class="text-red-400 ml-4">
                                {{ $t("rnprobe.summary") }}: {{ $t("rnprobe.failed") }}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import DialogUtils from "../../js/DialogUtils";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

export default {
    name: "RNProbePage",
    components: {
        MaterialDesignIcon,
    },
    data() {
        return {
            isRunning: false,
            destinationHash: null,
            fullName: "lxmf.delivery",
            probeSize: 16,
            probes: 1,
            wait: 0,
            results: [],
            summary: null,
            abortController: null,
        };
    },
    beforeUnmount() {
        this.stopProbe();
    },
    methods: {
        async startProbe() {
            if (this.isRunning) {
                return;
            }

            if (!this.destinationHash || this.destinationHash.length !== 32) {
                DialogUtils.alert(this.$t("rnprobe.invalid_hash"));
                return;
            }

            if (!this.fullName) {
                DialogUtils.alert(this.$t("rnprobe.provide_full_name"));
                return;
            }

            this.isRunning = true;
            this.abortController = new AbortController();
            this.results = [];
            this.summary = null;

            try {
                const response = await window.api.post(
                    "/api/v1/rnprobe",
                    {
                        destination_hash: this.destinationHash,
                        full_name: this.fullName,
                        size: this.probeSize,
                        probes: this.probes,
                        wait: this.wait,
                    },
                    {
                        signal: this.abortController.signal,
                    }
                );

                this.results = response.data.results || [];
                this.summary = {
                    sent: response.data.sent || 0,
                    delivered: response.data.delivered || 0,
                    timeouts: response.data.timeouts || 0,
                    failed: response.data.failed || 0,
                };
            } catch (e) {
                if (!window.api.isCancel(e)) {
                    console.error(e);
                    DialogUtils.alert(e.response?.data?.message || this.$t("rnprobe.failed_to_probe"));
                }
            } finally {
                this.isRunning = false;
            }
        },
        stopProbe() {
            this.isRunning = false;
            if (this.abortController) {
                this.abortController.abort();
            }
        },
        clearResults() {
            this.results = [];
            this.summary = null;
        },
    },
};
</script>
