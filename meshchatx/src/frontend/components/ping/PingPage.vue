<template>
    <!-- eslint-disable vue/no-v-html -->
    <div
        class="flex flex-col flex-1 overflow-hidden min-w-0 bg-gradient-to-br from-slate-50 via-slate-100 to-white dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-900"
    >
        <div class="flex-1 overflow-y-auto w-full px-4 md:px-5 lg:px-8 py-6">
            <div class="space-y-4 w-full max-w-4xl mx-auto">
                <div class="glass-card space-y-5">
                    <div class="space-y-2">
                        <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                            {{ $t("app.tools") }}
                        </div>
                        <div class="text-2xl font-semibold text-gray-900 dark:text-white">{{ $t("ping.title") }}</div>
                        <div class="text-sm text-gray-600 dark:text-gray-300">
                            <!-- eslint-disable-next-line vue/no-v-html -->
                            <span
                                v-html="
                                    $t('ping.description', {
                                        code: '<code class=\'font-mono text-xs\'>lxmf.delivery</code>',
                                    })
                                "
                            ></span>
                        </div>
                    </div>

                    <div class="grid md:grid-cols-2 gap-4">
                        <div>
                            <label class="glass-label">{{ $t("ping.destination_hash") }}</label>
                            <input
                                v-model="destinationHash"
                                type="text"
                                placeholder="e.g. 7b746057a7294469799cd8d7d429676a"
                                class="input-field font-mono"
                            />
                        </div>
                        <div>
                            <label class="glass-label">{{ $t("ping.timeout_seconds") }}</label>
                            <input v-model="timeout" type="number" min="1" class="input-field" />
                        </div>
                    </div>

                    <div class="flex flex-wrap gap-2">
                        <button v-if="!isRunning" type="button" class="primary-chip" @click="start">
                            <MaterialDesignIcon icon-name="play" class="w-4 h-4" />
                            {{ $t("ping.start_ping") }}
                        </button>
                        <button
                            v-else
                            type="button"
                            class="secondary-chip !text-red-600 dark:!text-red-300 !border-red-200 dark:!border-red-500/50"
                            @click="stop"
                        >
                            <MaterialDesignIcon icon-name="pause" class="w-4 h-4" />
                            {{ $t("ping.stop") }}
                        </button>
                        <button type="button" class="secondary-chip" @click="clear">
                            <MaterialDesignIcon icon-name="broom" class="w-4 h-4" />
                            {{ $t("ping.clear_results") }}
                        </button>
                        <button type="button" class="danger-chip" @click="dropPath">
                            <MaterialDesignIcon icon-name="link-variant-remove" class="w-4 h-4" />
                            {{ $t("ping.drop_path") }}
                        </button>
                    </div>

                    <div class="flex flex-wrap gap-2 text-xs font-semibold">
                        <span
                            :class="[
                                isRunning
                                    ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-200'
                                    : 'bg-gray-200 text-gray-700 dark:bg-zinc-800 dark:text-gray-200',
                                'rounded-full px-3 py-1',
                            ]"
                        >
                            {{ $t("ping.status") }}: {{ isRunning ? $t("ping.running") : $t("ping.idle") }}
                        </span>
                        <span
                            v-if="lastPingSummary?.duration"
                            class="rounded-full px-3 py-1 bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-200"
                        >
                            {{ $t("ping.last_rtt") }}: {{ lastPingSummary.duration }}
                        </span>
                        <span
                            v-if="lastPingSummary?.error"
                            class="rounded-full px-3 py-1 bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-200"
                        >
                            {{ $t("ping.last_error") }}: {{ lastPingSummary.error }}
                        </span>
                    </div>
                </div>

                <div class="glass-card flex flex-col min-h-[320px] space-y-3">
                    <div class="flex items-center justify-between gap-4">
                        <div>
                            <div class="text-sm font-semibold text-gray-900 dark:text-white">
                                {{ $t("ping.console_output") }}
                            </div>
                            <div class="text-xs text-gray-500 dark:text-gray-400">
                                {{ $t("ping.streaming_responses") }}
                            </div>
                        </div>
                        <div class="text-xs text-gray-500 dark:text-gray-400">seq #{{ seq }}</div>
                    </div>

                    <div
                        v-if="lastPingSummary && !lastPingSummary.error"
                        class="flex flex-wrap gap-2 text-xs text-gray-700 dark:text-gray-200"
                    >
                        <span v-if="lastPingSummary.hopsThere != null" class="stat-chip"
                            >{{ $t("rnprobe.hops") }} there: {{ lastPingSummary.hopsThere }}</span
                        >
                        <span v-if="lastPingSummary.hopsBack != null" class="stat-chip"
                            >{{ $t("rnprobe.hops") }} back: {{ lastPingSummary.hopsBack }}</span
                        >
                        <span v-if="lastPingSummary.rssi != null" class="stat-chip"
                            >{{ $t("rnprobe.rssi") }} {{ lastPingSummary.rssi }} dBm</span
                        >
                        <span v-if="lastPingSummary.snr != null" class="stat-chip"
                            >{{ $t("rnprobe.snr") }} {{ lastPingSummary.snr }} dB</span
                        >
                        <span v-if="lastPingSummary.quality != null" class="stat-chip"
                            >{{ $t("rnprobe.quality") }} {{ lastPingSummary.quality }}%</span
                        >
                        <span v-if="lastPingSummary.via" class="stat-chip"
                            >{{ $t("app.interfaces") }} {{ lastPingSummary.via }}</span
                        >
                    </div>

                    <div
                        id="results"
                        class="flex-1 overflow-y-auto rounded-2xl bg-black/80 text-emerald-300 font-mono text-xs p-3 space-y-1 shadow-inner border border-zinc-900"
                    >
                        <div v-if="pingResults.length === 0" class="text-emerald-500/80">
                            {{ $t("ping.no_pings_yet") }}
                        </div>
                        <div
                            v-for="(pingResult, index) in pingResults"
                            :key="`${index}-${pingResult}`"
                            class="whitespace-pre-wrap"
                        >
                            {{ pingResult }}
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
    name: "PingPage",
    components: {
        MaterialDesignIcon,
    },
    data() {
        return {
            isRunning: false,
            destinationHash: null,
            timeout: 10,
            seq: 0,
            pingResults: [],
            abortController: null,
            lastPingSummary: null,
        };
    },
    beforeUnmount() {
        this.stop();
    },
    mounted() {
        if (this.$route.query.hash) {
            this.destinationHash = this.$route.query.hash;
            if (this.$route.query.autostart === "1" || this.$route.query.autostart === "true") {
                this.start();
            }
        }
    },
    methods: {
        async start() {
            // do nothing if already running
            if (this.isRunning) {
                return;
            }

            // simple check to ensure destination hash is valid
            if (this.destinationHash == null || this.destinationHash.length !== 32) {
                DialogUtils.alert(this.$t("ping.invalid_hash"));
                return;
            }

            // simple check to ensure destination hash is valid
            if (this.timeout == null || this.timeout < 0) {
                DialogUtils.alert(this.$t("ping.timeout_must_be_number"));
                return;
            }

            // we are now running ping
            this.seq = 0;
            this.isRunning = true;
            this.abortController = new AbortController();

            // run ping until stopped
            while (this.isRunning) {
                // run ping
                await this.ping();

                // wait a bit before running next ping
                await this.sleep(1000);
            }
        },
        async stop() {
            this.isRunning = false;
            if (this.abortController) {
                this.abortController.abort();
            }
        },
        async clear() {
            this.pingResults = [];
            this.lastPingSummary = null;
        },
        async sleep(millis) {
            return new Promise((resolve) => setTimeout(resolve, millis));
        },
        async ping() {
            try {
                this.seq++;

                // ping destination
                const response = await window.api.get(`/api/v1/ping/${this.destinationHash}/lxmf.delivery`, {
                    signal: this.abortController.signal,
                    params: {
                        timeout: this.timeout,
                    },
                });

                const pingResult = response.data.ping_result;
                const rttMilliseconds = (pingResult.rtt * 1000).toFixed(3);
                const rttDurationString = `${rttMilliseconds}ms`;

                const info = [
                    `seq=${this.seq}`,
                    `duration=${rttDurationString}`,
                    `hops_there=${pingResult.hops_there}`,
                    `hops_back=${pingResult.hops_back}`,
                ];

                // add rssi if available
                if (pingResult.rssi != null) {
                    info.push(`rssi=${pingResult.rssi}dBm`);
                }

                // add snr if available
                if (pingResult.snr != null) {
                    info.push(`snr=${pingResult.snr}dB`);
                }

                // add signal quality if available
                if (pingResult.quality != null) {
                    info.push(`quality=${pingResult.quality}%`);
                }

                // add receiving interface
                info.push(`via=${pingResult.receiving_interface}`);

                // update ui
                this.addPingResult(info.join(" "));
                this.lastPingSummary = {
                    duration: rttDurationString,
                    hopsThere: pingResult.hops_there,
                    hopsBack: pingResult.hops_back,
                    rssi: pingResult.rssi,
                    snr: pingResult.snr,
                    quality: pingResult.quality,
                    via: pingResult.receiving_interface,
                };
            } catch (e) {
                // ignore cancelled error
                if (window.api.isCancel(e)) {
                    return;
                }

                console.log(e);

                // add ping error to results
                const message = e.response?.data?.message ?? e;
                this.addPingResult(`seq=${this.seq} error=${message}`);
                this.lastPingSummary = {
                    error: typeof message === "string" ? message : JSON.stringify(message),
                };
            }
        },
        async dropPath() {
            // simple check to ensure destination hash is valid
            if (this.destinationHash == null || this.destinationHash.length !== 32) {
                DialogUtils.alert(this.$t("ping.invalid_hash"));
                return;
            }

            try {
                const response = await window.api.post(`/api/v1/destination/${this.destinationHash}/drop-path`);
                DialogUtils.alert(response.data.message);
            } catch (e) {
                console.log(e);
                const message = e.response?.data?.message ?? `Failed to drop path: ${e}`;
                DialogUtils.alert(message);
            }
        },
        addPingResult(result) {
            this.pingResults.push(result);
            this.scrollPingResultsToBottom();
        },
        scrollPingResultsToBottom: function () {
            // next tick waits for the ui to have the new elements added
            this.$nextTick(() => {
                // set timeout with zero millis seems to fix issue where it doesn't scroll all the way to the bottom...
                setTimeout(() => {
                    const container = document.getElementById("results");
                    if (container) {
                        container.scrollTop = container.scrollHeight;
                    }
                }, 0);
            });
        },
    },
};
</script>
